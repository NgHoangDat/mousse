from copy import deepcopy
from typing import *

from .field import Field


class Accessor:
    def __init__(
        self,
        key: str,
        field: Field = None,
        strict: bool = False,
    ):
        self.key = key
        self.field = field
        self.strict = strict
        self.storage = {}

    def __get__(self, obj: Any, *args, **kwargs):
        if obj is None:
            return self

        if obj not in self.storage:
            self.storage[obj] = deepcopy(self.field.default)
        val = self.storage.get(obj)

        for getter in self.field.getters.values():
            if getter.static:
                val = getter(val)
            else:
                val = getter(obj, val)

        return val

    def __set__(self, obj: Any, val: Any):
        from .validator import validate

        for setter in self.field.setters.values():
            if setter.static:
                val = setter(val)
            else:
                val = setter(obj, val)

        if self.strict:
            assert validate(
                self.field.annotation, val
            ), f"Invalid datatype: require {self.field.annotation}, get {type(val)}"

        self.validate(obj, val)

        self.storage[obj] = val

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
