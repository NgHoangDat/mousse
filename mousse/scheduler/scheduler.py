import asyncio
import functools
from functools import partial

from datetime import datetime, timedelta
from typing import *
from typing import Callable

from .types import Task
from .time import get_next_runtime


class Scheduler:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.tasks: List[Task] = []
        self.actions: List[Callable] = []

    def schedule(
        self, caller: Optional[Callable], repeated: bool = False, **timedetail
    ):
        def decorator(func: Callable):
            task = Task()
            handle = func

            for key, value in func.__annotations__.items():
                if value is Task:
                    handle = partial(handle, **{key: task})

                if value is Scheduler:
                    handle = partial(handle, **{key: self})

            future = caller(self.loop, repeated=repeated, **timedetail)(handle)
            self.tasks.append(task)

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                task.handle = future.promise(*args, **kwargs)

            self.actions.append(wrapper)
            return func

        return decorator

    def ready(self):
        for action in self.actions:
            action()


def call_at(loop: asyncio.AbstractEventLoop, repeated: bool = False, **timedetail):
    def decorator(func, **options):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Task:
            action = partial(func, *args, **{**options, **kwargs})

            if not asyncio.iscoroutinefunction(action):
                action = asyncio.coroutine(action)

            task = Task()

            def reschedule():
                task.set_state("pending")
                next_run = get_next_runtime(datetime.now(), **timedetail)

                if next_run:
                    timestamp = (
                        next_run.timestamp() - datetime.now().timestamp() + loop.time()
                    )
                    task.handle = loop.call_at(when=timestamp, callback=run)
                else:
                    task.set_state("finished")

            def run():
                task.set_state("running")
                future = asyncio.ensure_future(action(), loop=loop)
                if repeated:
                    future.add_done_callback(lambda _: reschedule())
                else:
                    future.add_done_callback(lambda _: task.set_state("finished"))

            reschedule()
            return task

        setattr(func, "promise", wrapper)
        return func

    return decorator


def call_after(loop: asyncio.AbstractEventLoop, repeated: bool = False, **timedetail):
    def decorator(func, **options):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            action = partial(func, *args, **{**options, **kwargs})

            if not asyncio.iscoroutinefunction(action):
                action = asyncio.coroutine(action)

            task = Task()

            def reschedule():
                task.set_state("pending")
                timestamp = timedelta(**timedetail).total_seconds()
                task.handle = loop.call_later(delay=timestamp, callback=run)

            def run():
                task.set_state("running")
                future = asyncio.ensure_future(action(), loop=loop)
                if repeated:
                    future.add_done_callback(lambda _: reschedule())
                else:
                    future.add_done_callback(lambda _: task.set_state("finished"))

            reschedule()
            return task

        setattr(func, "promise", wrapper)
        return func

    return decorator
