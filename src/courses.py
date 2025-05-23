import requests, time, platform
from bs4 import BeautifulSoup
import notifier, notifierMac
import re
import time
from datetime import datetime

class Course:
    def __init__(self, crn: str, term: str):
        self.crn = crn
        self.term = term # default
        url = 'https://oscar.gatech.edu/bprod/bwckschd.p_disp_detail_sched?term_in='
        url += self.term + '&crn_in=' + self.crn
        with requests.Session() as s:
            with s.get(url) as page:
                soup = BeautifulSoup(page.content, 'html.parser')
                headers = soup.find_all('th', class_="ddlabel")
                self.name = headers[0].getText()

    def __get_prereqs(self):
        url = 'https://oscar.gatech.edu/bprod/bwckschd.p_disp_detail_sched?term_in='
        url += self.term + '&crn_in=' + self.crn

        with requests.Session() as s:
            with s.get(url) as page:
                soup = BeautifulSoup(page.content, 'html.parser')
                p = soup.find('td', class_="dddefault")
                txt = p.getText()
                idx = txt.index("Prerequisites:")
                return txt[idx:len(txt)-4]
    
    def __is_not_fodder(self, s: str) -> bool:
        fodder = ['undergraduate', 'graduate', 'level', 'grade', 'of', 'minimum', 'semester']
        tmp = s.lower()
        for fod in fodder:
            if fod == tmp: return False
        return True

    def get_prereqs(self):
        try:
            raw = self.__get_prereqs()
            block = ' '.join(list(filter(lambda el: self.__is_not_fodder(el), raw[raw.index("\n")+3:].split())))
            els = re.findall('\[[^\]]*\]|\([^\)]*\)|\"[^\"]*\"|\S+', block)
            parsed = ' '.join(els).replace('(Undergraduate ','(')
            return parsed
        except:
            return "None"

    def has_name(self) -> bool:
        return self.name != None
    
    def __get_registration_info(self, term: str):
        url = 'https://oscar.gatech.edu/bprod/bwckschd.p_disp_detail_sched?term_in='
        url += term + '&crn_in=' + self.crn

        try:
            with requests.Session() as s:
                with s.get(url) as page:
                    soup = BeautifulSoup(page.content, 'html.parser')
                    table = soup.find('caption', string='Registration Availability')
                    
                    if table is None:
                        print(f"Warning: Could not find registration information for CRN {self.crn}")
                        print("This might be because:")
                        print("1. The course is no longer available")
                        print("2. The CRN is invalid")
                        print("3. The term is incorrect")
                        print(f"URL: {url}")
                        return [0, 0, 0, 0, 0, 0]  # Return default values
                    
                    table = table.find_parent('table')
                    if table is None:
                        print(f"Warning: Could not find registration table for CRN {self.crn}")
                        return [0, 0, 0, 0, 0, 0]  # Return default values

                    data = [int(info.getText()) for info in table.findAll('td', class_='dddefault')]
                    return data
        except requests.RequestException as e:
            print(f"Network error while fetching data for CRN {self.crn}: {str(e)}")
            return [0, 0, 0, 0, 0, 0]  # Return default values
        except Exception as e:
            print(f"Error processing data for CRN {self.crn}: {str(e)}")
            return [0, 0, 0, 0, 0, 0]  # Return default values

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
