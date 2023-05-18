from copy import deepcopy
from functools import lru_cache
from typing import *

from .field import Field


class Accessor:
    def __init__(
        self,
        key: str,
        field: Field = None,
    ):
        self.key = key
        self.field = field
        self.storage = {}

    def __get__(self, obj: Any, *args, **kwargs):
        if obj is None:
            return self

        if id(obj) not in self.storage:
            if self.field.factory is not None:
                self.storage[id(obj)] = self.field.factory()
            else:
                self.storage[id(obj)] = deepcopy(self.field.default)
        val = self.storage.get(id(obj))

        for getter in self.field.getters.values():
            if getter.static:
                val = getter(val)
            else:
                val = getter(obj, val)

        return val

    def __set__(self, obj: Any, val: Any):
        from .validator import validate
        from .parser import parse

        val = parse(self.field.annotation, val)

        for setter in self.field.setters.values():
            if setter.static:
                val = setter(val)
            else:
                val = setter(obj, val)

        if self.field.strict:
            assert validate(
                self.field.annotation, val
            ), f"Invalid datatype: require {self.field.annotation}, get {type(val)}"

        self.validate(obj, val)

        self.storage[id(obj)] = val

    def validator(self, func: Callable = None, static: bool = True):
        return self.field.validator(func, static=static)

    def setter(self, func: Callable = None, static: bool = True):
        return self.field.setter(func, static=static)

    def getter(self, func: Callable = None, static: bool = True):
        return self.field.getter(func, static=static)

    def validate(self, obj: Any, val: Any) -> bool:
        for validator in self.field.validators.values():
            if validator.static:
                assert validator(
                    val
                ), f"Validation failed for [{self.key}]: {validator.__name__}"
            else:
                assert validator(
                    obj, val
                ), f"Validation failed for [{self.key}]: {validator.__name__}"
        return True


@lru_cache(maxsize=None)
def _get_accessors_info(cls: Any) -> Dict[str, Accessor]:
    return {}


@lru_cache(maxsize=None)
def _get_customs_info(cls: Any) -> Dict[str, Accessor]:
    return {}


def get_accessors_info(cls: Any, obj: Any = None) -> Dict[str, Accessor]:
    defaults = _get_accessors_info(cls)
    if obj is not None:
        customs = _get_customs_info(id(obj))
        customs.update(defaults)
        return customs

    return defaults
