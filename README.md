# Mousse

> Collections of my most used functions, classes and patterns. I was craving for a delicious mousse as I was comming up with the name.

## Installation

---

```sh
pip install -U mousse
```

## Components

---

### Dataclass

> This is a self-implement, minimal version of [pydantic](https://pydantic-docs.helpmanual.io), with some minor changes.

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
    items: List[str] = []

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
# anywhere.py

from typing import *
from mousse import get_config, asdict, asclass, Dataclass

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
# {
#     "foo": {
#         "name": "foo",
#         "number": 42.0,
#         "items": [
#             {
#                 "name": "banana",
#                 "price": 12
#             },
#             {
#                 "name": "egg",
#                 "price": 10
#             }
#         ]
#     },
#     "id": 1
# }

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


# compatible with asclass
bar = asclass(Bar, config)
print(bar)
# Bar(foo=Foo(name="foo", number=42.0, items=[Item(name="banana", price=12), Item(name="egg", price=10)]), id=1)
```

### Logger

---
> This module is for managing logging process, with pre-defined logging format and both file logging and stdout logging.

```py
# entry_point.py

from mousse import init_logger

init_logger(
    "foo", # key to identify logger,
    log_dir="logs" # log directory
)
```

```py
# anywhere.py

from mousse import get_logger

logger = get_logger("foo")
logger.info("This is", "my", "logger number:", 1)
# [2022-05-09 20:28:04] [43050 4345906560] [INFO] [2678317510.py.<cell line: 1>:1] This is my logger number: 1
```

The format of the log is:

```txt
[{date} {time}] [{process_id} {thread_id}] [{level}] [{file}.{caller}.{lineno}] {msg}
```

After `init_logger`, log with also be saved to the log directory

### Scheduler

---

> If you ever have the need to run a Python at a specific time, or periodically. This might come handy.

```py
import asyncio
from datetime import datetime

from mousse import call_at, call_after

loop = asyncio.get_event_loop()

# This function will be call at 11:05 everyday as long that the loop is still running
@call_at(loop=loop, repeated=True, hour=11, minute=5)
def show_actual_runtime(name: str):
    print(f"Actual time of {name}:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))


# This function will be call after every 10 minutes as long as the loop is still running
@call_after(loop=loop, repeated=True, minutes=10)
def show_current_runtime(name: str):
    print(f"Current time of {name}:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))

show_actual_runtime(name="call_now")
show_current_runtime(name="call_now")

show_actual_runtime.promise(name="call_at")
show_current_runtime.promis(name="call_after")

loop.run_forever()
```

Another way to run an application:

```py
from typing import *
from datetime import datetime
from mousse import Scheduler, call_at, call_after

scheduler = Scheduler()

now = datetime.now()

@scheduler.schedule(call_at, hour=now.hour, minute=now.minute + 5)
def five_minute_from_now():
    print("Five minute from start")
    print("Start time:", datetime.strftime(now, "%y-%m-%d %H:%M:%S"))
    print("End time:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))


@scheduler.schedule(call_after, minutes=1)
def one_minute_from_now():
    print("One minute from start")
    print("Start time:", datetime.strftime(now, "%y-%m-%d %H:%M:%S"))
    print("End time:", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))

scheduler.run()

```

The `scheduler` module is built upon two main function.

- `call_after`: call the function after some time

```py
def call_after(
    loop: asyncio.AbstractEventLoop = None, 
    repeated: bool = False, # Is the function called repeatly
    **timedetail # Is the parameters of datetime.timedelta
):
    ...
```

- `call_at`: call the function at specified time match the configuration

```py
def call_at(
    loop: asyncio.AbstractEventLoop = None, 
    repeated: bool = False, # Is the function called repeatly
    **timedetail # Will be explained below
):
    ...
```

`timedetail` includes these parameters: `year`, `month`, `week`, `weekday`, `day`, `hour`, `minute`, `second`, all with same format.

- None: ignore
- int: specific value
- (start, end, [step]): value in range(start, end, [step])
- [int, ...]: value in list

Note:

- a `tuple` in list is still considered as range and will be expanded.
- `week` has value from 1 - 5
- `weekday` has value from 1 - 7, starts from monday
- `hour` has value from 0 - 23
- `minute` and `second` hav value from 0 - 59
- If no suitable time found, the function won't be called