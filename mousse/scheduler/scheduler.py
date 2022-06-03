import asyncio
import functools
from datetime import datetime, timedelta
from functools import partial, wraps
from typing import *
from typing import Callable

from .time import get_next_runtime
from .types import Task, State

__all__ = ["Scheduler", "call_after", "call_at", "Schedulable", "schedulable"]


class Scheduler:
    def __init__(self, loop: asyncio.AbstractEventLoop = None):
        self.loop = loop or asyncio.get_event_loop()
        self.tasks: List[Task] = []
        self.actions: List[Callable] = []

    def schedule(
        self,
        caller: Optional[Callable],
        repeated: Union[bool, int] = False,
        **timedetail
    ):
        def decorator(func: Callable):
            handle = func

            for key, value in func.__annotations__.items():
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
    loop: asyncio.AbstractEventLoop = None,
    repeated: Union[bool, int] = False,
    **timedetail
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

            def reschedule(num_repeated: Union[bool, int]):
                task.set_state(State.pending)
                task.schedule = get_next_runtime(datetime.now(), **timedetail)

                if task.schedule:
                    timestamp = (
                        task.schedule.timestamp()
                        - datetime.now().timestamp()
                        + loop.time()
                    )
                    task.handle = loop.call_at(timestamp, run, num_repeated)
                else:
                    task.set_state(State.finish)

            def run(num_repeated: Union[bool, int]):
                task.set_state(State.running)
                future = asyncio.ensure_future(action(), loop=loop)
                if num_repeated:
                    future.add_done_callback(
                        lambda _: reschedule(
                            num_repeated
                            if type(num_repeated) is bool
                            else num_repeated - 1
                        )
                    )
                else:
                    future.add_done_callback(lambda _: task.set_state(State.finish))

            reschedule(repeated if type(repeated) is bool else repeated - 1)
            return task

        setattr(func, "promise", wrapper)
        return func

    return decorator


def call_after(
    loop: asyncio.AbstractEventLoop = None,
    repeated: Union[bool, int] = False,
    **timedetail
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

            def reschedule(num_repeated: Union[bool, int]):
                task.set_state(State.pending)
                timestamp = timedelta(**timedetail).total_seconds()
                task.handle = loop.call_later(timestamp, run, num_repeated)

            def run(num_repeated: Union[bool, int]):
                task.set_state(State.running)
                future = asyncio.ensure_future(action(), loop=loop)
                if num_repeated:
                    future.add_done_callback(
                        lambda _: reschedule(
                            num_repeated
                            if type(num_repeated) is bool
                            else num_repeated - 1
                        )
                    )
                else:
                    future.add_done_callback(lambda _: task.set_state(State.finish))

            reschedule(repeated if type(repeated) is bool else repeated - 1)
            return task

        setattr(func, "promise", wrapper)
        return func

    return decorator


class Schedulable:
    def __init__(self, func: Callable):
        self.func = func
        self.reset()

    def reset(self) -> "Schedulable":
        self.timedetail = {}
        self.loop = None
        self.caller = None
        self.repeated = False
        return self

    def at(self, repeated: Union[bool, int] = False, **timedetail) -> "Schedulable":
        self.timedetail = timedetail
        self.repeated = repeated
        self.caller = call_at
        return self

    def after(self, repeated: Union[bool, int] = False, **timedetail) -> "Schedulable":
        self.timedetail = timedetail
        self.repeated = repeated
        self.caller = call_after
        return self

    def within(self, loop: asyncio.AbstractEventLoop) -> "Schedulable":
        self.loop = loop
        return self

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def call(self, *args, **kwargs) -> Task:
        loop = self.loop or asyncio.get_running_loop()
        task = self.caller(loop=loop, repeated=self.repeated, **self.timedetail)(
            self.func
        )
        return task.promise(*args, **kwargs)


def schedulable(func: Callable) -> Schedulable:
    wrapper = Schedulable(func)
    wrapper = wraps(func)(wrapper)
    return wrapper
