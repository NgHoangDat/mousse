import asyncio
import functools
import operator
import re
from typing import *

from ..tools import mock
from .types import (
    Callable,
    Entry,
    GenericMeta,
    Hashable,
    Matcher,
    NoneType,
    Pattern,
    Result,
)


class __CustomClass:
    pass


async def __execute(action: Callable, *args, **kwargs) -> Any:
    if asyncio.iscoroutinefunction(action):
        return await action(*args, **kwargs)
    return action(*args, **kwargs)


def __remove_duplicate_ellipsis(sequences: Sequence[Any]):
    _sequences = []

    if sequences:
        _sequences.append(sequences[0])

        for i, elem in enumerate(sequences[1:]):
            if sequences[i] == elem and elem == Ellipsis:
                continue

            _sequences.append(elem)

    return _sequences


def __create_dfa(sequences: Sequence[Any]):
    sequences = __remove_duplicate_ellipsis(sequences)

    state = {"else": {}, "flag": False}

    fail = {"flag": False}
    fail["else"] = fail

    curr_state = state

    if sequences:
        next_state = curr_state
        for i, elem in enumerate(sequences):
            if elem == Ellipsis:
                curr_state["else"] = next_state
            else:
                if not curr_state["else"]:
                    curr_state["else"] = fail

                curr_state["key"] = elem

                next_state = {"else": {}, "flag": False}
                curr_state["val"] = next_state

            if i == len(sequences) - 1:
                next_state["flag"] = True
            else:
                curr_state = next_state

        if sequences[-1] == Ellipsis:
            next_state["else"] = next_state
        else:
            next_state["else"] = fail

    else:
        curr_state["else"] = fail

    return state


def __apply(matcher: Matcher) -> Matcher:
    @functools.wraps(matcher)
    def wrapper(action: Any, val: Any, key: Any = Any) -> Result:
        action = ensure_callable(action)
        if matcher(val, key):
            return True, action(val)

        return False, None

    return wrapper


def __apply_async(matcher: Matcher) -> Matcher:
    @functools.wraps(matcher)
    async def wrapper(action: Any, val: Any, key: Any = Any) -> Result:
        action = ensure_callable(action)

        if matcher(val, key):
            return True, await __execute(action, val)

        return False, None

    return wrapper


def __case(matcher: Matcher) -> Matcher:
    @functools.wraps(matcher)
    def wrapper(
        *entries: List[Entry],
        val: Any = None,
        accept_none: bool = False,
        accept_empty: bool = False
    ) -> Union[Callable, Result]:

        if len(entries) == 0 and not accept_empty:
            return functools.partial(
                wrapper, val=val, accept_none=accept_none, accept_empty=True
            )

        def handler(val: Any) -> Result:
            for key, action in entries:
                if matcher(val, key):
                    action = ensure_callable(action)
                    return True, action(val)
            return False, None

        if val is not None or accept_none:
            return handler(val)

        return handler

    return wrapper


def __case_async(matcher: Matcher) -> Matcher:
    @functools.wraps(matcher)
    async def wrapper(
        *entries: List[Entry],
        val: Any = None,
        accept_none: bool = False,
        accept_empty: bool = False
    ) -> Union[Callable, Result]:

        if len(entries) == 0 and not accept_empty:
            return ensure_coroutine(
                functools.partial(
                    wrapper, val=val, accept_none=accept_none, accept_empty=True
                )
            )

        async def handler(val: Any) -> Result:
            for key, action in entries:
                action = ensure_callable(action)

                if matcher(val, key):
                    return True, await __execute(action, val)

            return False, None

        if val is not None or accept_none:
            return await handler(val)

        return handler

    return wrapper


def __pipe(matcher: Matcher) -> Matcher:
    @functools.wraps(matcher)
    def wrapper(
        *entries: List[Entry],
        val: Any = None,
        accept_none: bool = False,
        accept_empty: bool = False,
        early_stop: bool = False
    ) -> Union[Callable, Result]:

        if len(entries) == 0 and not accept_empty:
            return functools.partial(
                wrapper,
                val=val,
                accept_none=accept_none,
                accept_empty=True,
                early_stop=early_stop,
            )

        def handler(val: Any) -> List[Result]:
            results = []
            for key, action in entries:
                if matcher(val, key):
                    action = ensure_callable(action)
                    results.append((True, action(val)))
                else:
                    if early_stop:
                        break
                    results.append((False, None))
            return results

        if val is not None or accept_none:
            return handler(val)

        return handler

    return wrapper


def __pipe_async(matcher: Matcher) -> Matcher:
    async def return_none():
        return None

    @functools.wraps(matcher)
    async def wrapper(
        *entries: List[Entry],
        val: Any = None,
        accept_none: bool = False,
        accept_empty: bool = False,
        early_stop: bool = False
    ) -> Union[Callable, Result]:

        if len(entries) == 0 and not accept_empty:
            return ensure_coroutine(
                functools.partial(
                    wrapper, val=val, accept_none=accept_none, accept_empty=True
                )
            )

        async def handler(val: Any) -> List[Result]:
            flags = []
            futures = []

            for key, action in entries:
                if matcher(val, key):
                    flags.append(True)
                    action = ensure_callable(action)
                    futures.append(__execute(action, val))
                else:
                    if early_stop:
                        break
                    flags.append(False)
                    futures.append(return_none())

            results = await asyncio.gather(*futures)
            return list(zip(flags, results))

        if val is not None or accept_none:
            return await handler(val)

        return handler

    return wrapper


def ensure_coroutine(action: Callable) -> Callable:
    if not asyncio.iscoroutinefunction(action):

        @functools.wraps(action)
        async def wrapper(*args, **kwargs):
            return action(*args, **kwargs)

        action = wrapper
    return action


def ensure_callable(action: Any) -> Callable:
    if not callable(action):
        action = mock(action)
    return action


def ATLEAST(num: int, *args):
    def match(_, matcher: Callable, val: Any):
        count = 0
        for i, key in enumerate(args):
            if matcher(val, key):
                count += 1

            if num - count > len(args) - i - 1:
                return False

            if count >= num:
                return True
        return False

    return type("", (__CustomClass,), {"match": match})()


def ATMOST(num: int, *args):
    def match(_, matcher: Callable, val: Any):
        count = 0
        for key in args:
            if matcher(val, key):
                count += 1

            if count > num:
                return False

        return True

    return type("", (__CustomClass,), {"match": match})()


def ANY(*args):
    return ATLEAST(1, *args)


def ALL(*args):
    return ATLEAST(len(args), *args)


def NONE(*args):
    return ATMOST(0, *args)


def INRANGE(start: int, end: int, step: int = 1):
    args = list(range(start, end, step))
    return ANY(*args)


def invoker(_matcher: Callable[[Any, Any], bool]) -> Callable:
    @functools.wraps(_matcher)
    def matcher(val: Any, key: Any) -> bool:
        if key is Any:
            return True
        return _matcher(val, key)

    setattr(matcher, "apply", __apply(matcher))
    setattr(matcher, "apply_async", __apply_async(matcher))

    setattr(matcher, "case", __case(matcher))
    setattr(matcher, "case_async", __case_async(matcher))

    setattr(matcher, "pipe", __pipe(matcher))
    setattr(matcher, "pipe_async", __pipe_async(matcher))

    return matcher


@invoker
def match_pattern(val: str, pattern: Union[str, Pattern]) -> bool:
    if type(pattern) is str:
        pattern = re.compile(pattern)
    return pattern.fullmatch(val)


@invoker
def match_value(val: Any, key: Any) -> bool:
    return operator.eq(val, key)


@invoker
def match_type(val: Any, key: type) -> bool:
    if key is NoneType and val is None:
        return True

    if type(val) is key:
        return True

    return False


@invoker
def match_generic(val: Any, key: GenericMeta) -> bool:
    if key is NoneType and val is not None:
        return False

    if key.__origin__ in (list, List, Sequence):
        if type(val) is list:
            mem_type = key.__args__[0]
            for mem in val:
                if not match_typing(mem, mem_type):
                    return False
            return True

    if key.__origin__ in (tuple, Tuple):
        for i, mem in enumerate(val):
            mem_type = key.__args__[min(i, len(key.__args__) - 1)]
            if mem_type is Ellipsis:
                mem_type = key.__args__[0]

            if not match_typing(mem, mem_type):
                return False

        return True

    if key.__origin__ is Union:
        for mem_type in key.__args__:
            if match_typing(val, mem_type):
                return True

    if key.__origin__ in (Dict, dict) and type(val) is dict:
        key_type, val_type = key.__args__
        for _key, _val in val.items():
            if not match_typing(_key, key_type) or not match_typing(_val, val_type):
                return False

        return True

    return False


@invoker
def match_typing(val: Any, key: Union[GenericMeta, type]) -> bool:
    matcher = match_generic if type(key) is GenericMeta else match_type
    return matcher(val, key)


@invoker
def match_sequence(vals: Sequence[Any], keys: Tuple[Any, ...]) -> bool:
    dfa = __create_dfa(keys)
    current_states = [dfa]

    for elem in vals:
        next_states = []
        ids = set()

        for state in current_states:
            if state["else"] == state:
                next_states.append(state)
                ids.add(id(state))

            if "key" in state and match(elem, state["key"]):
                next_state = state["val"]
            else:
                next_state = state["else"]

            if id(next_state) not in ids:
                next_states.append(next_state)
                ids.add(id(next_state))

        current_states.clear()
        current_states.extend(next_states)

    for state in current_states:
        if state["flag"]:
            return True

    return False


@invoker
def match_dict(vals: Dict[Hashable, Any], keys: Dict[Hashable, Any]) -> bool:
    for _key, val in vals.items():
        if _key not in keys:
            return False

        key = keys[_key]

        if not match(val, key):
            return False

    return True


@invoker
def match(val: Any, key: Any):
    if issubclass(type(key), __CustomClass):
        return key.match(match, val)

    if type(key) is type:
        return match_type(val, key)

    if type(key) is GenericMeta:
        return match_generic(val, key)

    if type(key) is dict:
        return match_dict(val, key)

    if type(key) in (tuple, list):
        return type(val) == type(key) and match_sequence(val, key)

    if type(key) is Pattern:
        return match_pattern(val, key)

    if not match_value(val, key):
        return False

    return True
