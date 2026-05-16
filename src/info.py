import sys
import argparse
from courses import Course, CourseList
from terms import resolve_term

parser = argparse.ArgumentParser(description='Show course availability information')
parser.add_argument(
    'season',
    choices=['spring', 'summer', 'fall'],
    type=str.lower,
    help='Desired upcoming term (Fall, Spring, Summer)'
)
parser.add_argument('crns', nargs='+', help='CRN numbers to inspect')

args = parser.parse_args()
term = resolve_term(args.season)

courses = []
for crn in args.crns:
    try:
        courses.append(Course(crn, term))
    except ValueError as exc:
        print(f"Could not initialize CRN {crn} for term {term}: {exc}", file=sys.stderr)

if not courses:
    print("No valid courses to show.", file=sys.stderr)
    sys.exit(1)

lst = CourseList(courses)
lst.get_info()
