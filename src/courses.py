import platform
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import notifier
import notifierMac


def empty_registration_info():
    return {
        "seats": 0,
        "taken": 0,
        "vacant": 0,
        "waitlist": {
            "seats": 0,
            "taken": 0,
            "vacant": 0,
        },
    }


class Course:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    BASE_URL = "https://registration.banner.gatech.edu/StudentRegistrationSsb/ssb"
    REQUEST_TIMEOUT = 15

    def __init__(self, crn: str, term: str):
        self.crn = crn
        self.term = term
        self._session = None
        self._init_session()
        self._fetch_course_name()

    def _init_session(self):
        """Initialize session and set term."""
        self._session = requests.Session()
        self._session.headers.update(Course.HEADERS)
        term_url = f"{Course.BASE_URL}/term/search?mode=search"

        try:
            response = self._session.post(
                term_url,
                data={"term": self.term},
                timeout=Course.REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise ValueError(
                f"Failed to initialize Banner session for term '{self.term}': {exc}"
            ) from exc

        if response.status_code != 200:
            raise ValueError(
                f"Failed to initialize Banner session for term '{self.term}'. "
                f"HTTP status: {response.status_code}"
            )

    def _fetch_course_name(self):
        """Fetch course name from Banner API using getClassDetails."""
        url = (
            f"{Course.BASE_URL}/searchResults/getClassDetails"
            f"?term={self.term}&courseReferenceNumber={self.crn}"
        )

        try:
            response = self._session.get(url, timeout=Course.REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise ValueError(
                f"Failed to fetch course data for CRN '{self.crn}' "
                f"and term '{self.term}': {exc}"
            ) from exc

        if response.status_code != 200:
            raise ValueError(
                f"Failed to fetch course data for CRN '{self.crn}' "
                f"and term '{self.term}'. HTTP status: {response.status_code}"
            )

        soup = BeautifulSoup(response.text, "html.parser")

        crn_span = soup.find("span", id="courseReferenceNumber")
        if not crn_span:
            raise ValueError(
                f"Course not found. CRN '{self.crn}' may be invalid for term '{self.term}'."
            )

        subject = soup.find("span", id="subject")
        course_num = soup.find("span", id="courseNumber")
        section = soup.find("span", id="sectionNumber")
        title = soup.find("span", id="courseTitle")

        subject_text = subject.get_text(strip=True) if subject else ""
        course_num_text = course_num.get_text(strip=True) if course_num else ""
        section_text = section.get_text(strip=True) if section else ""
        title_text = title.get_text(strip=True) if title else ""

        self.name = f"{subject_text} {course_num_text} - {section_text} - {title_text}"

    def __get_prereqs(self):
        # Prerequisites are not directly available in the current Banner API.
        return "None"

    def get_prereqs(self):
        return self.__get_prereqs()

    def has_name(self) -> bool:
        return self.name is not None

    def __get_registration_info(self, term: str):
        """Fetch enrollment info from Banner API using getEnrollmentInfo."""
        self.term = term

        if not self._session:
            self._init_session()

        url = (
            f"{Course.BASE_URL}/searchResults/getEnrollmentInfo"
            f"?term={term}&courseReferenceNumber={self.crn}"
        )

        try:
            response = self._session.get(url, timeout=Course.REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            print(
                f"Warning: Could not fetch registration information for CRN "
                f"{self.crn} in term {term}: {exc}"
            )
            return [0, 0, 0, 0, 0, 0]

        if response.status_code != 200:
            print(
                f"Warning: Could not fetch registration information for CRN "
                f"{self.crn} in term {term}. HTTP status: {response.status_code}"
            )
            return [0, 0, 0, 0, 0, 0]

        soup = BeautifulSoup(response.text, "html.parser")

        def extract_value(label):
            for span in soup.find_all("span", class_="status-bold"):
                if label in span.get_text():
                    next_span = span.find_next("span", dir="ltr")
                    if next_span:
                        try:
                            return int(next_span.get_text(strip=True).replace(",", ""))
                        except ValueError:
                            print(
                                f"Warning: Could not parse '{label}' for CRN "
                                f"{self.crn} in term {term}"
                            )
                            return 0
            return 0

        return [
            extract_value("Enrollment Maximum"),
            extract_value("Enrollment Actual"),
            extract_value("Enrollment Seats Available"),
            extract_value("Waitlist Capacity"),
            extract_value("Waitlist Actual"),
            extract_value("Waitlist Seats Available"),
        ]

    def get_registration_info(self, term: str):
        self.term = term
        data = self.__get_registration_info(term)

        if len(data) < 6:
            print(f"Warning: Invalid data received for CRN {self.crn}")
            return empty_registration_info()

        return {
            "seats": data[0],
            "taken": data[1],
            "vacant": data[2],
            "waitlist": {
                "seats": data[3],
                "taken": data[4],
                "vacant": data[5],
            },
        }

    def is_open_by_term(self, term: str) -> bool:
        return self.is_open_from_info(self.get_registration_info(term))

    def is_open(self) -> bool:
        return self.is_open_by_term(self.term)

    def waitlist_available_by_term(self, term: str) -> bool:
        return self.waitlist_available_from_info(self.get_registration_info(term))

    def waitlist_available(self) -> bool:
        return self.waitlist_available_by_term(self.term)

    def is_open_from_info(self, data) -> bool:
        return data["vacant"] > 0

    def waitlist_available_from_info(self, data) -> bool:
        return data["waitlist"]["vacant"] > 0

    def format_registration_info(self, data=None) -> str:
        data = data if data is not None else self.get_registration_info(self.term)

        res = f"{self.name}\n"
        for name in data:
            if name == "waitlist":
                continue
            res += f"{name}:\t{data[name]}\n"
        res += "waitlist open: {}\n".format(
            "yes" if self.waitlist_available_from_info(data) else "no"
        )
        res += f"prerequisites: {self.get_prereqs()}"
        return res

    def __str__(self) -> str:
        return self.format_registration_info()


class WaitlistNotifier(notifier.Notifier):
    def __init__(self, course: Course):
        self.title = "Waitlist Available"
        self.info, self.status_check = course.name, course.waitlist_available


class OpenCourseNotifier(notifier.Notifier):
    def __init__(self, course: Course):
        self.title = "Course Open"
        self.info, self.status_check = course.name, course.is_open


class WaitlistNotifierMac(notifierMac.Notifier):
    def __init__(self, course: Course):
        self.title = "Waitlist Available"
        self.info, self.status_check = course.name, course.waitlist_available


class OpenCourseNotifierMac(notifierMac.Notifier):
    def __init__(self, course: Course):
        self.title = "Course Open"
        self.info, self.status_check = course.name, course.is_open


class CourseList:
    def __init__(self, courses, sleep_time=30):
        self.courses = courses
        self.sleep_time = sleep_time

    def run_waitlist_notifiers(self):
        for course in self.courses:
            data = course.get_registration_info(course.term)
            if course.waitlist_available_from_info(data):
                notif = (
                    WaitlistNotifierMac(course)
                    if platform.system() == "Darwin"
                    else WaitlistNotifier(course)
                )
                print(course.format_registration_info(data))
                notif.run_force()
            time.sleep(0.025)

    def run_available_courses(self):
        for course in self.courses:
            data = course.get_registration_info(course.term)
            print(course.format_registration_info(data))
            if course.is_open_from_info(data):
                notif = (
                    OpenCourseNotifierMac(course)
                    if platform.system() == "Darwin"
                    else OpenCourseNotifier(course)
                )
                notif.run_force()
            time.sleep(0.025)

    def run_notifiers(self):
        while self.courses:
            self.run_available_courses()
            print(
                f"\nNext check in {self.sleep_time} seconds... "
                f"({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n"
            )
            time.sleep(self.sleep_time)

    def get_info(self):
        cnt = 0
        for course in self.courses:
            data = course.get_registration_info(course.term)
            message = course.format_registration_info(data)
            notif = notifier.Notifier("Info", message)
            if platform.system() == "Darwin":
                notif = notifierMac.Notifier("Info", message)
            if cnt > 0:
                print("\n------------------------------------------\n")
            print(message)
            notif.run_force()
            cnt += 1
