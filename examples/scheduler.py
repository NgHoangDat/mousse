from typing import *
from datetime import datetime
from mousse import Scheduler, call_at, call_after

scheduler = Scheduler()

now = datetime.now()

@scheduler.schedule(call_at, hour=now.hour, minute=now.minute + 5)
def five_minute_from_now():
    print("Five minute from start")
    print("Start time:", datetime.strftime(now, "%y-%m-%d %H:%M:%S"))
    print("End time:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))


@scheduler.schedule(call_after, minutes=1)
def one_minute_from_now():
    print("One minute from start")
    print("Start time:", datetime.strftime(now, "%y-%m-%d %H:%M:%S"))
    print("End time:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))

scheduler.run()
