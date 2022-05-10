from typing import *
from mousse import parse, Dataclass


class Foo(Dataclass):
    name: str
    number: float
    items: List[str] = []


print(parse(float, 1))  # 1.0
print(parse(Union[int, float], 1))  # 1
print(parse(Union[float, int], 1))  # 1.0

print(parse(Dict[str, Any], {1: 2, 2: 3}))  # {'1': 2, '2': 3}

print(parse(Dict[str, float], {1: 2, 2: 3}))  # {'1': 2.0, '2': 3.0}

print(
    parse(Foo, {"name": "foo", "number": 42.2, "items": [1, 2, 3]})
)  # Foo(name="foo", number=42.2, items=['1', '2', '3'])
