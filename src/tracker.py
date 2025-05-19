import sys
import argparse
from courses import Course, CourseList
from datetime import datetime

parser = argparse.ArgumentParser(description='Monitor course availability')
parser.add_argument('season', help='Desired upcoming term (Fall, Spring, Summer)')
parser.add_argument('crns', nargs='+', help='CRN numbers to monitor')
parser.add_argument('-t', '--time', type=int, default=30, help='Sleep time in seconds between checks (default: 30)')

args = parser.parse_args()

season = args.season
now = datetime.now()
term = ''

if season.lower() == 'spring':
    term = f'{now.year + 1}' + '02' if now.month > 4 else f'{now.year}' + '02'
else:
    term = f'{now.year}' + '05' if season.lower() == 'summer' else f'{now.year}' + '08'

courses = [Course(crn, term) for crn in args.crns]

lst = CourseList(courses, sleep_time=args.time)

print(f"Starting continuous monitoring for CRNs: {', '.join(args.crns)}")
print(f"Sleep time between checks: {args.time} seconds")
print("Press Ctrl+C to stop monitoring")
print("-" * 50)

try:
    lst.run_notifiers()
except KeyboardInterrupt:
    print("\nMonitoring stopped by user")
