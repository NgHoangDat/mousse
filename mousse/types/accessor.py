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
        self.validators = []

    def __get__(self, obj: Any, *args, **kwargs):
        if obj is None:
            return self

        if obj not in self.storage:
            self.storage[obj] = deepcopy(self.field.default)
        return self.storage.get(obj)

    def __set__(self, obj: Any, val: Any):
        from .validator import validate

        if self.strict:
            assert validate(
                self.field.annotation, val
            ), f"Invalid datatype: require {self.field.annotation}, get {type(val)}"

        self.validate(val)
        self.storage[obj] = val

    def validator(self, func: Callable):
        self.validators.append(func)
        return func

    def validate(self, val: Any) -> bool:
        for validator in self.validators:
            assert validator(
                val
            ), f"Validation failed for [{self.key}]: {validator.__name__}"
        return True
