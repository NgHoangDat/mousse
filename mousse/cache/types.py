from decimal import Decimal
from typing import *
from typing import Callable

Number = Union[float, int, Decimal]
Timer = Callable[[], Number]


class State:
    def __init__(
        self, key: Hashable, count: int = 1, earliest: Number = 0, latest: Number = 0
    ):
        self.key: Hashable = key
        self.count: int = count
        self.earliest: Number = earliest
        self.latest: Number = latest


Policy = Callable[[List[State]], State]


class Cache:
    def __init__(self):
        self.history: Dict[Hashable, State] = {}
        self.data: Dict[Hashable, Any] = {}

    def pop(self, value: Hashable):
        return self.data.pop(value), self.history.pop(value)
