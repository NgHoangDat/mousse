import inspect
from typing import *

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


def validate(G: Union[Generic, Type], obj: Any, strict: bool = True):
    if isinstance(G, get_args(Generic)):
        origin = get_origin(G) if G is not Any else Any

        if origin not in validators:
            return not strict

        validator = validators[origin]
        return validator(G, obj)

    return isinstance(obj, G)


@validator(List, Set, Sequence)
def validate_sequence(G: Generic, obj: Any):
    arg, *_ = get_args(G)
    origin = get_origin(G)
    return issubclass(type(obj), origin) and all(validate(arg, elem) for elem in obj)


@validator(Tuple)
def validate_tuple(G: Generic, obj: Any):
    args = get_args(G)
    if not issubclass(type(obj), tuple):
        return False

    if len(args) == 1 and len(obj) > 1:
        return False

    curr_idx = 0
    for i, elem in enumerate(obj):
        if not validate(args[curr_idx], elem):
            return False

        if i < len(obj) - 1:
            if curr_idx + 1 < len(args):
                if args[curr_idx + 1] != Ellipsis:
                    curr_idx += 1
                continue

            return False

    return True


@validator(Dict)
def validate_dict(G: Generic, obj: Any):
    if not issubclass(type(obj), dict):
        return False

    key_type, val_type = get_args(G)
    is_key_valid = all(validate(key_type, key) for key in obj.keys())
    is_val_valid = all(validate(val_type, val) for val in obj.values())

    return is_key_valid and is_val_valid


@validator(Union)
def validate_union(G: Generic, obj: Any):
    args = get_args(G)
    return any(validate(arg, obj) for arg in args)


@validator(type(None))
def validate_none(G: Generic, obj: Any):
    return obj is None


@validator(Any)
def validate_any(G: Generic, obj: Any):
    return True


@validator(Hashable)
def validate_hashable(G: Generic, obj: Any):
    return hasattr(obj, "__hash__")


@validator(Type)
def validate_type(G: Generic, obj: Any):
    arg, *_ = get_args(G)
    return arg == obj


@validator(Callable)
def validate_callable(G: Generic, obj: Any):
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
            Type[input_type], param.annotation
        ):
            return False

    if signature.return_annotation is not inspect._empty and not validate(
        Type[output_type], signature.return_annotation
    ):
        return False

    return True


@validator(Iterable, Iterator)
def validate_iterable(G: Generic, obj: Any):
    return isinstance(obj, Iterable)


class Validator:
    def __init__(self, field: str, func: Callable):
        self.field = field
        self.func = func


def validator(field: str, func: Callable = None):
    def decorator(func: Callable):
        return Validator(field, func)

    if func is not None:
        return decorator(func)

    return decorator
