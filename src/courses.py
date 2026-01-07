import requests, time, platform
from bs4 import BeautifulSoup
import notifier, notifierMac
import re
import time
from datetime import datetime

class Course:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    BASE_URL = 'https://registration.banner.gatech.edu/StudentRegistrationSsb/ssb'

    def __init__(self, crn: str, term: str):
        self.crn = crn
        self.term = term
        self._session = None
        self._init_session()
        self._fetch_course_name()

    def _init_session(self):
        """Initialize session and set term"""
        self._session = requests.Session()
        self._session.headers.update(Course.HEADERS)
        term_url = f'{Course.BASE_URL}/term/search?mode=search'
        self._session.post(term_url, data={'term': self.term})

    def _fetch_course_name(self):
        """Fetch course name from Banner API using getClassDetails"""
        url = f'{Course.BASE_URL}/searchResults/getClassDetails?term={self.term}&courseReferenceNumber={self.crn}'
        response = self._session.get(url)
        
        if response.status_code != 200:
            raise ValueError(f"Failed to fetch course data. HTTP status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if course exists
        crn_span = soup.find('span', id='courseReferenceNumber')
        if not crn_span:
            raise ValueError(f"Course not found. CRN '{self.crn}' may be invalid for term '{self.term}'.")
        
        # Extract course info
        subject = soup.find('span', id='subject')
        course_num = soup.find('span', id='courseNumber')
        section = soup.find('span', id='sectionNumber')
        title = soup.find('span', id='courseTitle')
        
        subject_text = subject.get_text(strip=True) if subject else ''
        course_num_text = course_num.get_text(strip=True) if course_num else ''
        section_text = section.get_text(strip=True) if section else ''
        title_text = title.get_text(strip=True) if title else ''
        
        self.name = f"{subject_text} {course_num_text} - {section_text} - {title_text}"

    def __get_prereqs(self):
        # Note: Prerequisites are not directly available in the new Banner API
        # This would require additional scraping or API calls
        return "None"
    
    def __is_not_fodder(self, s: str) -> bool:
        fodder = ['undergraduate', 'graduate', 'level', 'grade', 'of', 'minimum', 'semester']
        tmp = s.lower()
        for fod in fodder:
            if fod == tmp: return False
        return True

    def get_prereqs(self):
        return self.__get_prereqs()

    def has_name(self) -> bool:
        return self.name != None

    def __get_registration_info(self, term: str):
        """Fetch enrollment info from Banner API using getEnrollmentInfo"""
        self.term = term
        
        # Re-init session if term changed
        if not self._session:
            self._init_session()
        
        url = f'{Course.BASE_URL}/searchResults/getEnrollmentInfo?term={term}&courseReferenceNumber={self.crn}'
        
        try:
            response = self._session.get(url)
            if response.status_code != 200:
                print(f"Warning: Could not find registration information for CRN {self.crn}")
                return [0, 0, 0, 0, 0, 0]
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse enrollment info from HTML
            def extract_value(label):
                for span in soup.find_all('span', class_='status-bold'):
                    if label in span.get_text():
                        next_span = span.find_next('span', dir='ltr')
                        if next_span:
                            return int(next_span.get_text(strip=True))
                return 0
            
            max_enrollment = extract_value('Enrollment Maximum')
            enrollment = extract_value('Enrollment Actual')
            seats_available = extract_value('Enrollment Seats Available')
            wait_capacity = extract_value('Waitlist Capacity')
            wait_count = extract_value('Waitlist Actual')
            wait_available = extract_value('Waitlist Seats Available')
            
            return [max_enrollment, enrollment, seats_available, wait_capacity, wait_count, wait_available]
        except Exception as e:
            print(f"Error processing data for CRN {self.crn}: {str(e)}")
            return [0, 0, 0, 0, 0, 0]

    def get_registration_info(self, term: str):
        self.term = term
        data = self.__get_registration_info(term)

        if len(data) < 6:
            print(f"Warning: Invalid data received for CRN {self.crn}")
            return {
                'seats': 0,
                'taken': 0,
                'vacant': 0,
                'waitlist': {
                    'seats': 0,
                    'taken': 0,
                    'vacant': 0
                }
            }

        waitlist_data = {
            'seats': data[3],
            'taken': data[4],
            'vacant': data[5]
        }
        load = {
            'seats': data[0],
            'taken': data[1],
            'vacant': data[2],
            'waitlist': waitlist_data
        }
        return load

    def is_open_by_term(self, term: str) -> bool:
        return self.__get_registration_info(term)[2] > 0

    def is_open(self) -> bool:
        return self.is_open_by_term(self.term)

    def waitlist_available_by_term(self, term: str) -> bool:
        waitlist_data = self.get_registration_info(term)['waitlist']
        return waitlist_data['vacant'] > 0

    def waitlist_available(self) -> bool:
        return self.waitlist_available_by_term(self.term)

    def __str__(self) -> str:
        data = self.get_registration_info(self.term)
        res = "{}\n".format(self.name)
        for name in data:
            if name == 'waitlist': continue
            res += "{}:\t{}\n".format(name, data[name])
        res += "waitlist open: {}\n".format('yes' if self.waitlist_available() else 'no')
        res += "prerequisites: {}".format(self.get_prereqs())
        return res

class WaitlistNotifier(notifier.Notifier):
    def __init__(self, course: Course):
        self.title = 'Waitlist Available'
        self.info, self.status_check = course.name, course.waitlist_available

class OpenCourseNotifier(notifier.Notifier):
    def __init__(self, course: Course):
        self.title = 'Course Open'
        self.info, self.status_check = course.name, course.is_open

class WaitlistNotifierMac(notifierMac.Notifier):
    def __init__(self, course: Course):
        self.title = 'Waitlist Available'
        self.info, self.status_check = course.name, course.waitlist_available

class OpenCourseNotifierMac(notifierMac.Notifier):
    def __init__(self, course: Course):
        self.title = 'Course Open'
        self.info, self.status_check = course.name, course.is_open

class CourseList:
    def __init__(self, courses, sleep_time=30):
        self.courses = courses
        self.sleep_time = sleep_time

    def run_waitlist_notifiers(self):
        for course in self.courses:
            if course.waitlist_available():
                notif = WaitlistNotifierMac(course) if platform.system() == "Darwin" else WaitlistNotifier(course)
                print(course)
                notif.run_async()
                # self.courses.remove(course)
            time.sleep(0.025)

    def run_available_courses(self):
        for course in self.courses:
            print(course)
            if course.is_open():
                notif = OpenCourseNotifierMac(course) if platform.system() == "Darwin" else OpenCourseNotifier(course)
                notif.run_async()
                # self.courses.remove(course)
            time.sleep(0.025)

    def run_notifiers(self):
        while self.courses:  
            self.run_available_courses()
            print(f"\nNext check in {self.sleep_time} seconds... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
            time.sleep(self.sleep_time) # sleep for specified time
            # self.run_waitlist_notifiers()
    
    def get_info(self):
        cnt = 0
        for course in self.courses:
            notif = notifier.Notifier("Info", str(course))
            if platform.system() == "Darwin":
                notif = notifierMac.Notifier("Info", str(course))
            if cnt > 0:
                print('\n------------------------------------------\n')
            print(course)
            notif.run_force()
            cnt += 1
