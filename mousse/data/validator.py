import inspect
from typing import *

from .field import Field, get_fields_info
from .dataclass import Dataclass, Validator
from .types import Generic, get_args, get_origin

__all__ = ["validator", "Validator", "validate"]


validators = {}


def validator(*types: Type[Generic], func: Callable = None):
    def decorator(func: Callable):
        for _type in types:
            origin = get_origin(_type)
            if origin is None:
                origin = _type

            validators[origin] = func
        return func

    if func is not None:
        return decorator(func)

    return decorator


def validate(G: Union[Generic, Type], obj: Any, **kwargs):
    if isinstance(G, get_args(Generic)):
        origin = get_origin(G) if G is not Any else Any
        assert origin in validators, f"Validator not found"
        validator = validators[origin]
        return validator(G, obj)

    if issubclass(G, Dataclass):
        validator = validators[Dataclass]
        return validator(G, obj, **kwargs)

    return isinstance(obj, G)


@validator(List, Set, Sequence)
def validate_sequence(G: Generic, obj: Any, **kwargs):
    arg, *_ = get_args(G)
    origin = get_origin(G)
    return issubclass(type(obj), origin) and all(
        validate(arg, elem, **kwargs) for elem in obj
    )


@validator(Tuple)
def validate_tuple(G: Generic, obj: Any, **kwargs):
    args = get_args(G)
    if not issubclass(type(obj), tuple):
        return False

    if len(args) == 1 and len(obj) > 1:
        return False

    curr_idx = 0
    for i, elem in enumerate(obj):
        if not validate(args[curr_idx], elem, **kwargs):
            return False

        if i < len(obj) - 1:
            if curr_idx + 1 < len(args):
                if args[curr_idx + 1] != Ellipsis:
                    curr_idx += 1
                continue

            return False

    return True


@validator(Dict)
def validate_dict(G: Generic, obj: Any, **kwargs):
    if not issubclass(type(obj), dict):
        return False

    key_type, val_type = get_args(G)
    is_key_valid = all(validate(key_type, key, **kwargs) for key in obj.keys())
    is_val_valid = all(validate(val_type, val, **kwargs) for val in obj.values())

    return is_key_valid and is_val_valid


@validator(Union)
def validate_union(G: Generic, obj: Any, **kwargs):
    args = get_args(G)
    return any(validate(arg, obj, **kwargs) for arg in args)


@validator(type(None))
def validate_none(G: Generic, obj: Any, **kwargs):
    return obj is None


@validator(Any)
def validate_any(G: Generic, obj: Any, **kwargs):
    return True


@validator(Hashable)
def validate_hashable(G: Generic, obj: Any, **kwargs):
    return hasattr(obj, "__hash__")


@validator(Type)
def validate_type(G: Generic, obj: Any, **kwargs):
    arg, *_ = get_args(G)
    return arg == obj


@validator(Callable)
def validate_callable(G: Generic, obj: Any, **kwargs):
    if not hasattr(obj, "__call__"):
        return False

    args = get_args(G)
    if len(args) == 0:
        return True

    inputs_type, output_type = args
    signature = inspect.signature(obj)

    params = iter(signature.parameters.values())
    for input_type in inputs_type:
        param = next(params)
        if param.annotation is not inspect._empty and not validate(
            Type[input_type], param.annotation, **kwargs
        ):
            return False

    if signature.return_annotation is not inspect._empty and not validate(
        Type[output_type], signature.return_annotation, **kwargs
    ):
        return False

    return True


@validator(Iterable, Iterator)
def validate_iterable(G: Generic, obj: Any, **kwargs):
    return isinstance(obj, Iterable)


@validator(Dataclass)
def validate_dataclass(
    G: Dataclass, obj: Any, as_schema: bool = False, strict: bool = False, **kwargs
):
    from .parser import asclass
    if not as_schema:
        return isinstance(obj, G)

    if not isinstance(obj, Mapping):
        return False

    fields = get_fields_info(G)
    fields = {
        field.alias if field.alias is not None else key: field
        for key, field in fields.items()
    }

    for key, val in obj.items():
        if key not in fields:
            if strict:
                return False
            continue

        field: Field = fields.pop(key)
        if not validate(
            field.annotation, val, as_schema=as_schema, strict=strict, **kwargs
        ):
            return False
        
        if field.validator is not None:
            if issubclass(field.annotation, Dataclass):
                try:
                    val = asclass(field.annotation, val)
                except AssertionError:
                    return False
                
                if not field.validator(val):
                    return False

    for key, field in fields.items():
        if field.default == Ellipsis:
            return False

    return True


def validator(field: str, func: Callable = None):
    def decorator(func: Callable):
        return Validator(field, func)

    if func is not None:
        return decorator(func)

    return decorator
