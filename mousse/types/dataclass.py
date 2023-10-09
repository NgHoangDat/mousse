from copy import copy, deepcopy
from inspect import Parameter, Signature
from typing import *

from .accessor import Accessor, get_accessors_info
from .field import Field, get_fields_info

__all__ = ["Dataclass", "DataMetaclass"]


class DataMetaclass(type):
    def __new__(
        cls,
        name: str,
        bases: Tuple[type, ...],
        data: Dict[str, Any],
        accessor: Type[Accessor] = Accessor,
        strict: int = 0,
        dynamic: bool = False,
    ):
        parameters = [Parameter("self", Parameter.POSITIONAL_ONLY)]
        defaults = []
        fields = {}
        accessors = {}

        for base in bases[::-1]:
            if issubclass(base, Dataclass):
                accessors.update(get_accessors_info(base))

        if "__annotations__" in data:
            annotations = data.pop("__annotations__")
            for key, dtype in annotations.items():
                default_val = Ellipsis
                if key in data:
                    default_val = data.pop(key)

                if isinstance(default_val, Field):
                    field = default_val
                    default_val = field.default
                else:
                    field = Field(default_val)

                field.annotation = dtype
                if field.private is None:
                    field.private = key.startswith("_")

                fields[key] = field
                if field.strict is None:
                    field.strict = strict

                accessors[key] = accessor(key, field=field)
                data[key] = accessors[key]
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
            fields = get_fields_info(self.__class__, self)
            for key, val in kwargs.items():
                if key in fields or dynamic:
                    setattr(self, key, val)

            for key, val in accessors.items():
                val.validate(self, getattr(self, key))

            if hasattr(self, "__build__"):
                self.__build__(*args, **kwargs)

        def __setattr__(self, key: str, val: Any):
            fields = get_fields_info(self.__class__, self)
            accessors = get_accessors_info(self.__class__, self)
            if key not in fields and dynamic:
                dtype = type(val)

                field = Field(val, factory=dtype)
                field.annotation = dtype
                field.private = key.startswith("_")
                field.strict = strict
                fields[key] = field

                accessors[key] = accessor(key, field=field)
                object.__setattr__(self, key, accessors[key])

            accessors[key].__set__(self, val)

        def __getattr__(self, key: str):
            if key == "__class__":
                return object.__getattribute__(self, key)

            accessors = get_accessors_info(self.__class__, self)
            if key in accessors:
                return accessors[key].__get__(self)

            return object.__getattribute__(self, key)

        def __copy__(self):
            cls = self.__class__

            result = cls.__new__(cls)
            result.__dict__.update(self.__dict__)

            fields = get_fields_info(cls, result)
            fields.update(get_fields_info(cls, self))

            for key in fields:
                val = getattr(self, key)
                setattr(result, key, copy(val))

            return result

        def __deepcopy__(self, memo: Dict[int, Any]):
            cls = self.__class__
            result = cls.__new__(cls)
            memo[id(self)] = result

            for k, v in self.__dict__.items():
                setattr(result, k, deepcopy(v, memo))

            fields = get_fields_info(cls, result)
            fields.update(get_fields_info(cls, self))

            for key in fields:
                val = getattr(self, key)
                setattr(result, key, deepcopy(val))

            return result

        def __getstate__(self):
            from .parser import asdict

            return asdict(self)

        def __setstate__(self, state: Dict[str, Any]):
            from .parser import asclass

            new = asclass(self.__class__, state)
            for key in get_fields_info(self.__class__, self):
                val = getattr(new, key)
                setattr(self, key, val)

        def __iter__(self):
            for key in get_fields_info(self.__class__, self):
                yield key, getattr(self, key)

        def __repr__(self):
            components = []
            for key in get_fields_info(self.__class__, self):
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
        data["__setattr__"] = __setattr__
        data["__getattribute__"] = __getattr__
        data["__copy__"] = __copy__
        data["__deepcopy__"] = __deepcopy__
        data["__getstate__"] = __getstate__
        data["__setstate__"] = __setstate__
        data["__iter__"] = __iter__
        data["__repr__"] = __repr__

        cls = super().__new__(cls, name, bases, data)
        fields_info = get_fields_info(cls)

        for base in bases[::-1]:
            if issubclass(base, Dataclass):
                fields_info.update(get_fields_info(base))

        fields_info.update(fields)

        get_accessors_info(cls).update(accessors)
        return cls


class Dataclass(metaclass=DataMetaclass):
    pass
