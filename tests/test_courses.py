import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import courses


CLASS_DETAILS_HTML = """
<span id="courseReferenceNumber">12345</span>
<span id="subject">CS</span>
<span id="courseNumber">1331</span>
<span id="sectionNumber">A</span>
<span id="courseTitle">Intro to Object Oriented Programming</span>
"""

ENROLLMENT_HTML = """
<span class="status-bold">Enrollment Maximum</span><span dir="ltr">30</span>
<span class="status-bold">Enrollment Actual</span><span dir="ltr">28</span>
<span class="status-bold">Enrollment Seats Available</span><span dir="ltr">2</span>
<span class="status-bold">Waitlist Capacity</span><span dir="ltr">10</span>
<span class="status-bold">Waitlist Actual</span><span dir="ltr">4</span>
<span class="status-bold">Waitlist Seats Available</span><span dir="ltr">6</span>
"""


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, get_responses=None, post_response=None):
        self.headers = {}
        self.calls = []
        self.get_responses = list(get_responses or [])
        self.post_response = post_response or FakeResponse()

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        if isinstance(self.post_response, Exception):
            raise self.post_response
        return self.post_response

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        response = self.get_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class CourseRequestTests(unittest.TestCase):
    def make_course(self, session):
        with patch.object(courses.requests, "Session", return_value=session):
            return courses.Course("12345", "202608")

    def test_course_requests_use_timeout_and_parse_enrollment(self):
        session = FakeSession(
            get_responses=[
                FakeResponse(text=CLASS_DETAILS_HTML),
                FakeResponse(text=ENROLLMENT_HTML),
            ]
        )

        course = self.make_course(session)
        info = course.get_registration_info("202608")

        self.assertEqual(course.name, "CS 1331 - A - Intro to Object Oriented Programming")
        self.assertEqual(info["seats"], 30)
        self.assertEqual(info["taken"], 28)
        self.assertEqual(info["vacant"], 2)
        self.assertEqual(info["waitlist"]["vacant"], 6)

        for method, _, kwargs in session.calls:
            self.assertIn(method, {"post", "get"})
            self.assertEqual(kwargs["timeout"], courses.Course.REQUEST_TIMEOUT)

    def test_enrollment_http_error_returns_empty_info_with_warning(self):
        session = FakeSession(
            get_responses=[
                FakeResponse(text=CLASS_DETAILS_HTML),
                FakeResponse(status_code=500, text="server error"),
            ]
        )
        course = self.make_course(session)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            info = course.get_registration_info("202608")

        self.assertEqual(info, courses.empty_registration_info())
        self.assertIn("HTTP status: 500", output.getvalue())

    def test_enrollment_request_exception_returns_empty_info_with_warning(self):
        session = FakeSession(
            get_responses=[
                FakeResponse(text=CLASS_DETAILS_HTML),
                requests.Timeout("timed out"),
            ]
        )
        course = self.make_course(session)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            info = course.get_registration_info("202608")

        self.assertEqual(info, courses.empty_registration_info())
        self.assertIn("timed out", output.getvalue())


class CourseListTests(unittest.TestCase):
    def test_run_available_courses_reuses_single_registration_fetch(self):
        class FakeCourse:
            crn = "12345"
            term = "202608"

            def __init__(self):
                self.fetch_count = 0

            def get_registration_info(self, term):
                self.fetch_count += 1
                return courses.empty_registration_info()

            def format_registration_info(self, data):
                return "formatted course info"

            def is_open_from_info(self, data):
                return False

        course = FakeCourse()
        course_list = courses.CourseList([course])

        with contextlib.redirect_stdout(io.StringIO()):
            with patch.object(courses.time, "sleep"):
                course_list.run_available_courses()

        self.assertEqual(course.fetch_count, 1)

    def test_run_available_courses_sends_from_cached_open_snapshot(self):
        class FakeCourse:
            crn = "12345"
            term = "202608"
            name = "Open Course"

            def __init__(self):
                self.fetch_count = 0

            def get_registration_info(self, term):
                self.fetch_count += 1
                return {
                    "seats": 1,
                    "taken": 0,
                    "vacant": 1,
                    "waitlist": {"seats": 0, "taken": 0, "vacant": 0},
                }

            def format_registration_info(self, data):
                return "formatted course info"

            def is_open_from_info(self, data):
                return data["vacant"] > 0

            def is_open(self):
                raise AssertionError("should not re-check course availability")

        course = FakeCourse()
        course_list = courses.CourseList([course])

        with contextlib.redirect_stdout(io.StringIO()):
            with patch.object(courses.platform, "system", return_value="Linux"):
                with patch.object(courses.OpenCourseNotifier, "run_force") as run_force:
                    with patch.object(courses.time, "sleep"):
                        course_list.run_available_courses()

        self.assertEqual(course.fetch_count, 1)
        run_force.assert_called_once_with()

    def test_run_waitlist_notifiers_sends_from_cached_waitlist_snapshot(self):
        class FakeCourse:
            crn = "12345"
            term = "202608"
            name = "Waitlist Course"

            def __init__(self):
                self.fetch_count = 0

            def get_registration_info(self, term):
                self.fetch_count += 1
                return {
                    "seats": 1,
                    "taken": 1,
                    "vacant": 0,
                    "waitlist": {"seats": 3, "taken": 1, "vacant": 2},
                }

            def format_registration_info(self, data):
                return "formatted course info"

            def waitlist_available_from_info(self, data):
                return data["waitlist"]["vacant"] > 0

            def waitlist_available(self):
                raise AssertionError("should not re-check waitlist availability")

        course = FakeCourse()
        course_list = courses.CourseList([course])

        with contextlib.redirect_stdout(io.StringIO()):
            with patch.object(courses.platform, "system", return_value="Linux"):
                with patch.object(courses.WaitlistNotifier, "run_force") as run_force:
                    with patch.object(courses.time, "sleep"):
                        course_list.run_waitlist_notifiers()

        self.assertEqual(course.fetch_count, 1)
        run_force.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
