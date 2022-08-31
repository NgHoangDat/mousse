from typing import *
from mousse import validate, Dataclass


class Foo(Dataclass):
    name: str
    number: float
    items: List[str] = []


Number = Union[int, float]

assert validate(int, 1)  # True
assert not validate(int, 1.0)  # False

assert validate(Number, 1)  # True
assert validate(Number, 1.0)  # True

assert validate(Dict[str, Any], {"a": 1, "b": "a"})  # True

assert not validate(Dict[str, int], {"a": 1, "b": "a"})  # False

assert validate(Tuple[int, float], (1, 1.2))  # True
assert not validate(Tuple[int, float], (1.0, 1.2))  # False
assert validate(Tuple[Number, Number], (1, 1.2))  # True

foo = Foo(name="foo", number=42.0, items=["banana", "egg"])
assert validate(Foo, foo)  # True
assert validate(List[Foo], [foo])  # True
assert not validate(List[Foo], (foo,))  # False
assert validate(Sequence[Foo], (foo,))  # True
assert validate(Foo, {"name": "foo", "number": 42.0}, as_schema=True)
