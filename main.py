from caldav.elements import dav, cdav
from datetime import datetime, timedelta
from dateutil.parser import parse
from pytz import timezone
import caldav
import json
import os
import pandas as pd
import numpy as np
import uuid


def parse_todos():
    ### read todo.txt
    with open(os.environ['todo_path'], 'r') as f:
        todos = [i.strip() for i in f.readlines()]
        
    ### processing
    df = pd.DataFrame()
    df['todo'] = todos

    # extract tag
    tag_regex = r'(@[a-z]+)'
    df['tag'] = df['todo'].str.extract(tag_regex)
    df['tag'] = df['tag'].str.replace('@', '')
    df['todo'] = df['todo'].str.replace(tag_regex, '')

    # remove add date
    add_date_regex = r'(^[0-9]{4}-[0-9]{2}-[0-9]{2})'
    df['todo'] = df['todo'].str.replace(add_date_regex, '')

    # extract due date
    due_date_regex = r'due:([0-9]{4}-[0-9]{2}-[0-9]{2})'
    df['due_date'] = df['todo'].str.extract(due_date_regex)
    df['todo'] = df['todo'].str.replace(due_date_regex, '')

    # final cleanup
    df = df[df.due_date.notnull()]
    df['todo'] = df['todo'].str.strip()
    df['todo'] = np.where(df['tag'].notnull(), '[' + df['tag'].str.upper() + ']' + ' ' + df['todo'], df['todo'])
    df.drop('tag', axis=1, inplace=True)

    return json.loads(df.to_json(orient='records'))


def create_vcal(todo):
    ### create params
    summary = todo['todo']

    utc = timezone('UTC')

    today = datetime.now(timezone('Asia/Bangkok')
                         ).replace(hour=0, minute=0, second=0)
    today = today.astimezone(utc)
    today = today.strftime("%Y%m%dT%H%M%SZ")

    task_start_date = todo['due_date']
    task_start_date = timezone('Asia/Bangkok').localize(parse(task_start_date))
    task_start_date = task_start_date.astimezone(utc)
    task_due_date = task_start_date+timedelta(days=1)

    task_start_date = task_start_date.strftime("%Y%m%dT%H%M%SZ")
    task_due_date = task_due_date.strftime("%Y%m%dT%H%M%SZ")

    uid = uuid.uuid4()

    ######## LEAVE BODY INDENTATION AS-IS, LEADING TAB BREAKS THE ACCEPTED BODY FORMAT ########
    body = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:FringeDivision
BEGIN:VTODO
UID:{uid}@example.com
DTSTAMP:{today}
DTSTART;VALUE=DATE:{task_start_date}
DUE;VALUE=DATE:{task_due_date}
SUMMARY:{summary}
END:VTODO
END:VCALENDAR
    """

    return body


def return_calendar_object():
    ### init caldav
    client = caldav.DAVClient(
        url=os.environ['caldav_url'], username=os.environ['caldav_username'], password=os.environ['caldav_password'])
    my_principal = client.principal()

    calendar_name = os.environ['calendar_name']
    calendars = my_principal.calendars()
    calendar = [i for i in calendars if i.get_properties(
        [dav.DisplayName()])['{DAV:}displayname'] == calendar_name][0]

    ### doesn't work with mailbox.org
    # ### delete calendar & create an empty one
    # calendar_name = os.environ['calendar_name']
    # calendars = my_principal.calendars()

    # # delete
    # calendar = [i for i in calendars if i.get_properties(
    #     [dav.DisplayName()])['{DAV:}displayname'] == calendar_name][0]
    # calendar.delete()

    # # create
    # calendar = my_principal.make_calendar(
    #     name=calendar_name, supported_calendar_component_set=['VTODO'])

    return calendar


if __name__ == "__main__":
    todos = parse_todos()
    calendar = return_calendar_object()

    ### clear entries
    print('clearing entries...')
    for i in calendar.todos():
        i.delete()

    ### add todo to caldav
    for todo in todos:
        vcal = create_vcal(todo)
        calendar.add_todo(vcal)

        task_name = todo['todo']
        print(f'added: {task_name}')
