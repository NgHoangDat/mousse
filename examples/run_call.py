import asyncio
from calendar import week, weekday
from datetime import datetime

from mousse import call_at, call_after

loop = asyncio.get_event_loop()

# This function will be call at 11:05 everyday as long that the loop is still running
@call_at(loop=loop, repeated=True, month=5, weekday=3, hour=1, minute=5, second=10, microsecond=14)
def show_actual_runtime(name: str):
    print(f"Actual time of {name}:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))


# This function will be call after every 10 minutes as long as the loop is still running
@call_after(loop=loop, repeated=True, minutes=10)
def show_current_runtime(name: str):
    print(f"Current time of {name}:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))

show_actual_runtime(name="call_now")
show_current_runtime(name="call_now")

show_actual_runtime.promise(name="call_at")
show_current_runtime.promise(name="call_after")

# loop.run_forever()
