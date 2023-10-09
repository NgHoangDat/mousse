from collections import OrderedDict
from enum import Enum
from functools import lru_cache
from typing import *

__all__ = ["Field", "get_fields_info", "Strictness"]


class Strictness(int, Enum):
    IGNORE: int = 0
    CONVERT: int = 10
    REJECT: int = 100


class Function(NamedTuple):
    func: Callable
    static: bool = False

    def __call__(self, *args: Any, **kwargs: Dict[str, Any]) -> Any:
        return self.func(*args, **kwargs)


class Field:
    def __init__(
        self,
        default: Any = Ellipsis,
        alias: str = None,
        freeze: bool = False,
        private: bool = None,
        strict: int = None,
        factory: Callable = None,
    ) -> None:
        self.default = default
        self.alias = alias
        self.freeze = freeze
        self.annotation = None
        self.private = private
        self.strict = strict
        self.factory = factory

        self.validators = OrderedDict()
        self.setters = OrderedDict()
        self.getters = OrderedDict()

    def validator(self, func: Callable = None, static: bool = True):
        def decorator(func: Callable):
            self.validators[id(func)] = Function(func, static)
            return func

        if func is not None:
            return decorator(func)

        return decorator

    def setter(self, func: Callable = None, static: bool = True):
        def decorator(func: Callable):
            self.setters[id(func)] = Function(func, static)
            return func

        if func is not None:
            return decorator(func)

        return decorator

    def getter(self, func: Callable = None, static: bool = True):
        def decorator(func: Callable):
            self.getters[id(func)] = Function(func, static)
            return func

        if func is not None:
            return decorator(func)

        return decorator


def get_fields_info(cls: Any, ins: Any = None) -> Dict[str, Field]:
    defaults = _get_fields_info(cls)
    if ins is not None:
        custom = _get_custome_info(id(ins))
        custom.update(defaults)
        return custom

    return defaults


@lru_cache(typed=True)
def _get_fields_info(cls: Any) -> Dict[str, Field]:
    return {}


@lru_cache(typed=True)
def _get_custome_info(ins: Any) -> Dict[str, Field]:
    return {}
