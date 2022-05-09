from copy import deepcopy
from typing import *

from .field import Field
from .validator import validate


class Accessor:
    def __init__(
        self,
        key: str,
        field: Field = None,
        validators: List[str] = None,
        strict: bool = False,
    ):
        self.key = key
        self.field = field
        self.validators = validators or []
        self.strict = strict
        self.storage = {}

    def __get__(self, obj: Any, *args, **kwargs):
        if obj not in self.storage:
            self.storage[obj] = deepcopy(self.field.default)
        return self.storage.get(obj)

    def __set__(self, obj: Any, val: Any):
        if self.strict:
            assert validate(
                self.field.annotation, val
            ), f"Invalid datatype: require {self.field.annotation}, get {type(val)}"

        for validator_name in self.validators:
            validator = getattr(obj, validator_name)
            assert validator(val), f"Validation failed at: {validator_name}"

        self.storage[obj] = val
