import pickle

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
bar = Bar(index=1, foo=foo)
print(bar.foo)
# Foo(name="foo", number=42.0, items=['banana', 'egg'])

# convert back to dictionary
bar_dict = asdict(bar)
print(bar_dict)
# {'foo': {'name': 'foo', 'number': 42.0, 'items': ['banana', 'egg']}, 'id': 1}

# convert back to dataclass
bar = asclass(Bar, bar_dict)
print("asclass", bar)
# Bar(foo=Foo(name="foo", number=42.0, items=['banana', 'egg']), index=1)

# load from file (.json, .yaml)
bar = asclass(Bar, path="examples/bar.json")
print("from_file", bar)
# Bar(foo=Foo(name="foo", number=42.0, items=['banana', 'egg']), index=1)

pickle_bar = pickle.dumps(bar)
unpickle_bar = pickle.loads(pickle_bar)
print("pickle", unpickle_bar)
