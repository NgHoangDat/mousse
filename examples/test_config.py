from typing import *

from mousse import Dataclass, asclass, asdict, get_config, load_config


class Item(Dataclass):
    name: str
    price: int


class Foo(Dataclass):
    name: str
    number: float
    items: List[Item]


class Bar(Dataclass):
    foo: Foo
    id: int


config = get_config("foo")

load_config(
    "foo",  # to identified a key for the configuration,
    path="examples/config.yaml",  # also support json
)

print(config)
print(config.foo)
print(config.foo.items[0].price)

config_data = asdict(config)
print(config_data)

# compatible with asclass
bar = asclass(Bar, config)
print(bar)
# Bar(foo=Foo(name="foo", number=42.0, items=[Item(name="banana", price=12), Item(name="egg", price=10)]), id=1)
