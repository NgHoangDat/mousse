import asyncio
from enum import Enum
from typing import *
from typing import Callable


class State(str, Enum):
    idle: str = "idle"
    canncel: str = "cancel"
    pending: str = "pending"
    running: str = "running"
    finish: str = "finish"


class Task:
    def __init__(self):
        self.state: State = State.idle
        self.schedule = None
        self.handle: Optional[asyncio.Handle] = None

    def cancel(self, *args, **kwargs):
        if self.handle:
            self.handle.cancel()
        self.state = State.canncel

    def set_state(self, state: State, *args, **kwargs):
        self.state = state

    async def wait(self, interval: float = 1):
        while True:
            await asyncio.sleep(interval)
            if self.state in (State.canncel, State.finish):
                break
