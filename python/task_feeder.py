#!/usr/bin/env python

"""
Create a set of fake tasks for testing
"""

from datetime import datetime
import pytz
import pprint

# Dallas (SoftLayer) is the official timezone
OFFICIAL_TIMEZONE = 'US/Central'


def init_team_tasks(team_timezone):
    '''
    Create the list of N fake tasks
    '''

    california = pytz.timezone(team_timezone)
    dallas = pytz.timezone(OFFICIAL_TIMEZONE)

    #local = datetime.now(pytz.timezone("US/Pacific"))

    tasks = []
    task_id = 1

    # Day 1
    local_start_day1 = datetime(2013, 6, 18, 8, 0, 0, tzinfo=california)
    local_end_day1 = datetime(2013, 6, 18, 18, 0, 0, tzinfo=california)
    official_start_day1 = local_start_day1.astimezone(dallas)
    official_end_day1 = local_end_day1.astimezone(dallas)

    for i in range(5):
        task = {'id': task_id, 'name': 'This is task ' + str(task_id),
                'start': official_start_day1, 'end': official_end_day1}
        tasks.append(task)
        task_id += 1

    # Day 2
    local_start_day2 = datetime(2013, 6, 19, 8, 0, 0, tzinfo=california)
    local_end_day2 = datetime(2013, 6, 19, 18, 0, 0, tzinfo=california)
    official_start_day2 = local_start_day2.astimezone(dallas)
    official_end_day2 = local_end_day2.astimezone(dallas)

    for i in range(5):
        task = {'id': task_id, 'name': 'This is task ' + str(task_id),
                'start': official_start_day2, 'end': official_end_day2}
        tasks.append(task)
        task_id += 1

    # Day 3
    local_start_day3 = datetime(2013, 6, 20, 8, 0, 0, tzinfo=california)
    local_end_day3 = datetime(2013, 6, 20, 18, 0, 0, tzinfo=california)
    official_start_day3 = local_start_day3.astimezone(dallas)
    official_end_day3 = local_end_day3.astimezone(dallas)
    for i in range(5):
        task = {'id': task_id, 'name': 'This is task ' + str(task_id),
                'start': official_start_day3, 'end': official_end_day3}
        tasks.append(task)
        task_id += 1

    '''print 'Local start day1 (California): ', str(local_start_day1)
    print 'Local end day1 (California): ', str(local_end_day1)
    print 'Official start day1 (Dallas): ', str(official_start_day1)
    print 'Official end day1 (Dallas): ', str(official_end_day1)'''

    return tasks


my_tasks = init_team_tasks('US/Pacific')
pprint.pprint(my_tasks)
