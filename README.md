# Mousse

> Collections of my most used functions, classes and patterns. I was craving for a delicious mousse as I was comming up with the name. I


## Installation
---

```sh
pip install -U mousse
```

## Components

---
### Dataclass
> This is a self-implement, minimal version of [pydantic](https://pydantic-docs.helpmanual.io), with some minar changes.

```py
from typing import *
from mousse import Dataclass, asdict, asclass, Field

class Foo(Dataclass):
    name: str
    number: float
    items: List[str] = []


class Bar(Dataclass):
    foo: Foo
    index: int = Field(..., alias="id")


foo = Foo(
    name="foo", 
    number=42.0, 
    items=["banana", "egg"]
)
bar = Bar(id=1, foo=foo)
print(bar.foo)
# Foo(name="foo", number=42.0, items=['banana', 'egg'])

#convert back to dictionary
bar_dict = asdict(bar)
print(bar_dict)
# {'foo': {'name': 'foo', 'number': 42.0, 'items': ['banana', 'egg']}, 'id': 1}

#conver back to dataclass
bar = asclass(Bar, bar_dict)
print(bar)
# Bar(foo=Foo(name="foo", number=42.0, items=['banana', 'egg']), index=1)

# load from file (.json, .yaml)
bar = asclass(Bar, path="bar.json")
print(bar)
# Bar(foo=Foo(name="foo", number=42.0, items=['banana', 'egg']), index=1)

```

Some helper functions are:
- `validate`: Check data type of variable

```py
from typing import *
from mousse import validate, Dataclass

class Foo(Dataclass):
    name: str
    number: float
    items: List[str] = []

Number = Union[int, float]

validate(int, 1) # True
validate(int, 1.0) # False

validate(Number, 1) # True
validate(Number, 1.0) # True

validate(Dict[str, Any], {
    "a": 1,
    "b": "a"
}) # True

validate(Dict[str, int], {
    "a": 1,
    "b": "a"
}) # False

validate(Tuple[int, float], (1, 1.2)) # True
validate(Tuple[int, float], (1.0, 1.2)) # False
validate(Tuple[Number, Number], (1, 1.2)) # True

foo = Foo(
    name="foo", 
    number=42.0, 
    items=["banana", "egg"]
)
validate(Foo, foo) # True
validate(List[Foo], [foo]) # True
validate(List[Foo], (foo,)) # False
validate(Sequence[Foo], (foo,)) # True

```

- `parse`: Attempt to parse data

```py
from typing import *
from mousse import parse, Dataclass

class Foo(Dataclass):
    name: str
    number: float
    items: List[str] = []s

parse(float, 1) # 1.0
parse(Union[int, float], 1) # 1
parse(Union[float, int], 1) # 1.0

parse(Dict[str, Any], {
    1: 2,
    2: 3
}) # {'1': 2, '2': 3}

parse(Dict[str, float], {
    1: 2,
    2: 3
}) # {'1': 2.0, '2': 3.0}

parse(Foo, {
    "name": "foo",
    "number": 42.2,
    "items": [1, 2, 3]
}) # Foo(name="foo", number=42.2, items=['1', '2', '3'])
```
---
### Config

> This is how I manage the configuration of my application. By creating a Config object that can be loaded once and refered everywhere. Of course, by default, the Config object cannot be changed by convention means. A changing config during runtime is evil.

#### Usage

```py
# entry_point.py

from mousse import load_config

load_config(
    "foo", # to identified a key for the configuration,
    path="config.yaml" # also support json
)

# config.yaml
# foo:
#   name: foo
#   number: 42.0
#   items:
#     - name: banana
#       price: 12
#     - name: egg
#       price: 10
# id: 1
```

```py
from mousse import get_config

# This can be called anytime
config = get_config("foo")

# before load_config
print(config)
# Config()

# after load_config
print(config)
# Config(foo=Config(items=[Config(price=12), Config(price=10)]), id=1)

print(config.foo)
# Config(items=[Config(price=12), Config(price=10)])

print(config.foo.items[0].price)
# 12

# reassignment is forbidden 
config.foo = "bar"
# AssertionError: Permission denied

# compatible with asdict
config_data = asdict(config)
print(config_data)

```