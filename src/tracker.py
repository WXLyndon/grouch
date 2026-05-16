import sys
import argparse
from courses import Course, CourseList
from terms import resolve_term

parser = argparse.ArgumentParser(description='Monitor course availability')
parser.add_argument(
    'season',
    choices=['spring', 'summer', 'fall'],
    type=str.lower,
    help='Desired upcoming term (Fall, Spring, Summer)'
)
parser.add_argument('crns', nargs='+', help='CRN numbers to monitor')
parser.add_argument(
    '-t',
    '--time',
    type=int,
    default=30,
    help='Sleep time in seconds between checks (default: 30)'
)

args = parser.parse_args()

if args.time <= 0:
    parser.error('--time must be greater than 0')

term = resolve_term(args.season)

courses = []
for crn in args.crns:
    try:
        courses.append(Course(crn, term))
    except ValueError as exc:
        print(f"Could not initialize CRN {crn} for term {term}: {exc}", file=sys.stderr)

if not courses:
    print("No valid courses to monitor.", file=sys.stderr)
    sys.exit(1)

lst = CourseList(courses, sleep_time=args.time)

print(
    "Starting continuous monitoring for CRNs: "
    f"{', '.join(course.crn for course in courses)}"
)
print(f"Sleep time between checks: {args.time} seconds")
print("Press Ctrl+C to stop monitoring")
print("-" * 50)

try:
    lst.run_notifiers()
except KeyboardInterrupt:
    print("\nMonitoring stopped by user")
