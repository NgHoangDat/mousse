import re
from typing import *
from typing import Callable, Hashable

try:
    from typing import GenericMeta
except ImportError:
    from typing import _GenericAlias as GenericMeta


try:
    from re import Pattern
except ImportError:
    Pattern = type(re.compile("", 0))


Matcher = Callable[[Any, Any], bool]
Entry = Tuple[Any, Callable]
Result = Tuple[bool, Any]
NoneType = type(None)
