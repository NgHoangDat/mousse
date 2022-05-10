from typing import *
from mousse import Dataclass, asdict, asclass, Field


class Foo(Dataclass):
    name: str
    number: float
    items: List[str] = []


class Bar(Dataclass):
    foo: Foo
    index: int = Field(..., alias="id")


foo = Foo(name="foo", number=42.0, items=["banana", "egg"])
bar = Bar(id=1, foo=foo)
print(bar.foo)
# Foo(name="foo", number=42.0, items=['banana', 'egg'])

# convert back to dictionary
bar_dict = asdict(bar)
print(bar_dict)
# {'foo': {'name': 'foo', 'number': 42.0, 'items': ['banana', 'egg']}, 'id': 1}

# conver back to dataclass
bar = asclass(Bar, bar_dict)
print(bar)
# Bar(foo=Foo(name="foo", number=42.0, items=['banana', 'egg']), index=1)

# load from file (.json, .yaml)
bar = asclass(Bar, path="examples/bar.json")
print(bar)
# Bar(foo=Foo(name="foo", number=42.0, items=['banana', 'egg']), index=1)
