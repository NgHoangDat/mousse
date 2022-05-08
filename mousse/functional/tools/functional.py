import asyncio
import functools
import operator as op

from typing import *
from typing import Callable

from toolz.curried import (
    apply,
    comp,
    complement,
    compose,
    compose_left,
    concat,
    concatv,
    count,
    curry,
    diff,
    first,
    flip,
    frequencies,
    identity,
    interleave,
    isdistinct,
    isiterable,
    juxt,
    last,
    memoize,
    merge_sorted,
    peek,
    pipe,
    second,
    thread_first,
    thread_last,
    merge,
    merge_with,
    accumulate,
    assoc,
    assoc_in,
    cons,
    countby,
    dissoc,
    do,
    drop,
    filter,
    get,
    get_in,
    groupby,
    interpose,
    itemfilter,
    itemmap,
    iterate,
    join,
    keyfilter,
    keymap,
    map,
    mapcat,
    nth,
    partial,
    partition,
    partition_all,
    partitionby,
    peekn,
    pluck,
    random_sample,
    reduce,
    reduceby,
    remove,
    sliding_window,
    sorted,
    tail,
    take,
    take_nth,
    topk,
    unique,
    update_in,
    valfilter,
    valmap,
)


@curry
def case(
    x: Any,
    *,
    predicate: Callable[..., bool],
    action: Callable[..., Any],
    otherwise: Optional[Callable[..., Any]] = None
) -> Any:
    if predicate(x):
        return action(x)
    elif otherwise:
        return otherwise(x)
    else:
        return x


def mock(value: Any, raw: bool = True):
    def func(*args, **kwargs):
        if callable(value) and not raw:
            return value()
        return value

    return func


def excepts(
    _func: Optional[Callable] = None,
    exception: Type[Exception] = Exception,
    handler: Optional[Callable] = None,
):
    def decorator(func: Callable):
        if not exception:
            return func

        if asyncio.iscoroutinefunction(func) or asyncio.iscoroutinefunction(handler):

            async def wrapper(*args, **kwargs):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    return func(*args, **kwargs)
                except exception:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler(*args, **kwargs)
                    return handler(*args, **kwargs)

        else:

            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except exception:
                    return handler(*args, **kwargs)

        return functools.wraps(func)(wrapper)

    if _func:
        return decorator(_func)

    return decorator


@curry
def eq(this: Any, that: Any) -> bool:
    return op.eq(this, that)


@curry
def gt(this: Any, that: Any) -> bool:
    return op.gt(this, that)


@curry
def lt(this: Any, that: Any) -> bool:
    return op.lt(this, that)


@curry
def ge(this: Any, that: Any) -> bool:
    return op.ge(this, that)


@curry
def le(this: Any, that: Any) -> bool:
    return op.le(this, that)


@curry
def is_instance(bases: Union[Type, Tuple[Type, ...]], obj: Any) -> bool:
    return isinstance(obj, bases)


@curry
def is_subclass(bases: Union[Type, Tuple[Type, ...]], cls: Type) -> bool:
    return issubclass(cls, bases)


@curry
def is_in(
    collection: Union[List[Any], Dict[Any, Any], Tuple[Any, ...]], val: Any
) -> bool:
    return val in collection


@curry
def peek_nth(index: int, seq: List[Any], default: Optional[Any] = None) -> Any:
    if is_instance((list, tuple), seq):
        if 0 <= index < len(seq):
            return seq[index]
        return default

    for i, val in enumerate(seq):
        if i == index:
            return val

    return default


def all(*predicates: List[Callable[[Any], bool]]) -> Callable[[Any], bool]:
    def func(*args, **kwargs):
        for predicate in predicates:
            if not predicate(*args, **kwargs):
                return False
        return True

    return func


def any(*predicates: List[Callable[[Any], bool]]) -> Callable[[Any], bool]:
    def func(*args, **kwargs):
        for predicate in predicates:
            if predicate(*args, **kwargs):
                return True
        return False

    return func


@curry
def sort(iterable: Iterable[Any], key: Callable[[Any], Any]):
    return sorted(iterable, key=key)


def partial_update(
    origin: Dict[Hashable, Any], data: Dict[Hashable, Any]
) -> Dict[Hashable, Any]:
    updated = origin.copy()
    for key, value in data.items():
        if key in updated:
            if type(updated[key]) is dict and type(value) is dict:
                updated[key] = partial_update(updated[key], value)
                continue
        updated[key] = value
    return updated
