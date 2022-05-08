from copy import copy, deepcopy
from inspect import Parameter, Signature
from typing import *

from .accessor import Accessor
from .field import Field, get_fields_info
from .validator import Validator

__all__ = ["Dataclass", "DataMetaclass"]


class DataMetaclass(type):
    def __new__(
        cls,
        name: str,
        bases: Tuple[type, ...],
        data: Dict[str, Any],
        accessor: Type[Accessor] = Accessor,
        strict: bool = False,
    ):
        validators = {}
        for key, val in data.items():
            if isinstance(val, Validator):
                if val.field not in validators:
                    validators[val.field] = []

                validators[val.field].append(key)
                data[key] = val.func

        keys = []
        parameters = [Parameter("self", Parameter.POSITIONAL_ONLY)]
        defaults = []
        fields = {}

        if "__annotations__" in data:
            annotations = data.pop("__annotations__")
            for key, dtype in annotations.items():
                default_val = None
                if key in data:
                    default_val = data.pop(key)

                if isinstance(default_val, Field):
                    field = default_val
                    default_val = field.default
                else:
                    field = Field(default_val or Ellipsis)

                field.annotation = dtype
                if field.exclude is None:
                    field.exclude = key.startswith("_")

                fields[key] = field

                data[key] = accessor(
                    key, field=field, validators=validators.get(key), strict=strict
                )
                keys.append(key)
                parameters.append(
                    Parameter(
                        key,
                        Parameter.KEYWORD_ONLY,
                        default=default_val,
                        annotation=dtype,
                    )
                )
                defaults.append(default_val)

        def __init__(self, *args, **kwargs):
            for key, val in kwargs.items():
                if key in keys:
                    setattr(self, key, val)
            self.build(*args, **kwargs)

        def __copy__(self):
            cls = self.__class__

            result = cls.__new__(cls)
            result.__dict__.update(self.__dict__)

            for key in keys:
                val = getattr(self, key)
                setattr(result, key, copy(val))

            return result

        def __deepcopy__(self, memo: Dict[int, Any]):
            cls = self.__class__
            result = cls.__new__(cls)
            memo[id(self)] = result

            for k, v in self.__dict__.items():
                setattr(result, k, deepcopy(v, memo))

            for key in keys:
                val = getattr(self, key)
                setattr(result, key, deepcopy(val))

            return result

        def __iter__(self):
            for key in keys:
                yield key, getattr(self, key)

        def __repr__(self):
            components = []
            for key in keys:
                val = getattr(self, key)
                if isinstance(val, str):
                    components.append(f'{key}="{val}"')
                else:
                    components.append(f"{key}={val}")

            components = ", ".join(components)
            return f"{name}({components})"

        setattr(__init__, "__signature__", Signature(parameters=parameters))
        __init__.__defaults__ = tuple(defaults)

        data["__init__"] = __init__
        data["__copy__"] = __copy__
        data["__deepcopy__"] = __deepcopy__
        data["__iter__"] = __iter__
        data["__repr__"] = __repr__

        cls = super().__new__(cls, name, bases, data)
        fields_info = get_fields_info(cls)
        fields_info.update(fields)

        return cls


class Dataclass(metaclass=DataMetaclass):
    def build(self, *args, **kwargs):
        pass
