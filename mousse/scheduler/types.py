import asyncio

from typing import *
from typing import Callable


class Task:
    def __init__(self):
        self.state: str = "idle"
        self.schedule = None
        self.handle: Optional[asyncio.Handle] = None

    def cancel(self, *args, **kwargs):
        if self.handle:
            self.handle.cancel()
        self.state = "canceled"

    def set_state(self, state: str, *args, **kwargs):
        self.state = state
