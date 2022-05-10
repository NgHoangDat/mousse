import asyncio
import functools
from datetime import datetime, timedelta
from functools import partial
from typing import *
from typing import Callable

from .time import get_next_runtime
from .types import Task, State

__all__ = ["Scheduler", "call_after", "call_at"]


class Scheduler:
    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.tasks: List[Task] = []
        self.actions: List[Callable] = []

    def schedule(
        self, caller: Optional[Callable], repeated: bool = False, **timedetail
    ):
        def decorator(func: Callable):
            handle = func

            for key, value in func.__annotations__.items():
                if value is Task:
                    handle = partial(handle, **{key: task})

                if value is Scheduler:
                    handle = partial(handle, **{key: self})

            future = caller(self.loop, repeated=repeated, **timedetail)(handle)

            def wrapper(*args, **kwargs):
                self.tasks.append(future.promise(*args, **kwargs))

            self.actions.append(wrapper)
            return func

        return decorator

    def ready(self):
        self.tasks.clear()
        for action in self.actions:
            action()

    def run(self, interval: float = 1):
        self.ready()

        async def runner():
            while True:
                await asyncio.sleep(interval)
                done = False
                for task in self.tasks:
                    if task.state in (State.pending, State.running):
                        break
                    done = True

                if done:
                    break

        self.loop.run_until_complete(runner())


def call_at(
    loop: asyncio.AbstractEventLoop = None, repeated: bool = False, **timedetail
):
    if loop is None:
        loop = asyncio.get_event_loop()

    def decorator(func, **options):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Task:
            action = partial(func, *args, **{**options, **kwargs})

            if not asyncio.iscoroutinefunction(action):
                action = asyncio.coroutine(action)

            task = Task()

            def reschedule():
                task.set_state(State.pending)
                task.schedule = get_next_runtime(datetime.now(), **timedetail)

                if task.schedule:
                    timestamp = (
                        task.schedule.timestamp()
                        - datetime.now().timestamp()
                        + loop.time()
                    )
                    task.handle = loop.call_at(when=timestamp, callback=run)
                else:
                    task.set_state(State.finish)

            def run():
                task.set_state(State.running)
                future = asyncio.ensure_future(action(), loop=loop)
                if repeated:
                    future.add_done_callback(lambda _: reschedule())
                else:
                    future.add_done_callback(lambda _: task.set_state(State.finish))

            reschedule()
            return task

        setattr(func, "promise", wrapper)
        return func

    return decorator


def call_after(
    loop: asyncio.AbstractEventLoop = None, repeated: bool = False, **timedetail
):
    if loop is None:
        loop = asyncio.get_event_loop()

    def decorator(func, **options):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            action = partial(func, *args, **{**options, **kwargs})

            if not asyncio.iscoroutinefunction(action):
                action = asyncio.coroutine(action)

            task = Task()

            def reschedule():
                task.set_state(State.pending)
                timestamp = timedelta(**timedetail).total_seconds()
                task.handle = loop.call_later(delay=timestamp, callback=run)

            def run():
                task.set_state(State.running)
                future = asyncio.ensure_future(action(), loop=loop)
                if repeated:
                    future.add_done_callback(lambda _: reschedule())
                else:
                    future.add_done_callback(lambda _: task.set_state(State.finish))

            reschedule()
            return task

        setattr(func, "promise", wrapper)
        return func

    return decorator
