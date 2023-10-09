import asyncio
import functools
import operator
import time
from collections.abc import Hashable
from typing import *
from typing import Callable

from ..functional import case, compose, curry, excepts, is_instance, map, mock
from .policies import lru
from .types import Cache, Number, Policy, State, Timer


def generate_hash(generator: Callable[[Hashable], Hashable]):
    def hash_func(*args, **kwargs):
        keys, values = (
            zip(*sorted(kwargs.items(), key=operator.itemgetter(0)))
            if kwargs
            else ((), ())
        )
        hash_list = lambda lst: hash_func(*lst)
        hash_dict = lambda dct: hash_func(**dct)

        get_hash = case(
            predicate=is_instance(list),
            action=hash_list,
            otherwise=case(
                predicate=is_instance(dict),
                action=hash_dict,
                otherwise=case(
                    predicate=is_instance(Hashable),
                    action=hash,
                    otherwise=lambda val: val.__repr__(),
                ),
            ),
        )

        join_value = "-".join(compose(map(str), map(get_hash))(args + keys + values))
        return generator(join_value.encode())

    return hash_func


@curry
def update_history(
    key: Hashable,
    value: Any,
    timestamp: Number,
    cache: Cache,
    maxsize: int,
    policy: Policy,
):
    if len(cache.history) == maxsize:
        deleted = policy(list(cache.history.values()))
        cache.pop(deleted.key)

    current = State(key=key, earliest=timestamp, latest=timestamp)
    cache.history[key] = current
    cache.data[key] = value


def __check_and_remove_outdated(
    hash_generator: Callable, cache: Cache, ttl: int, now: float, key: Hashable
):
    data, state = None, None
    if ttl > 0 and key in cache.history and cache.history[key].earliest < now - ttl:
        data, state = cache.pop(key)

    return data, state


def memoize(
    _func: Optional[Callable] = None,
    maxsize: int = 256,
    ttl: Number = 0,
    timer: Timer = time.time,
    policy: Policy = lru,
    hash_generator: Callable[[Hashable], Hashable] = hash,
    catch_exception: Optional[Type[Exception]] = None,
):

    cache = Cache()
    update_cache_history = update_history(cache=cache, maxsize=maxsize, policy=policy)
    hash_generator = generate_hash(hash_generator)

    def decorator(func: Callable):

        if asyncio.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):
                now = timer()
                key = hash_generator(*args, **kwargs)
                data, _ = __check_and_remove_outdated(
                    hash_generator, cache, ttl, now, key
                )

                if key not in cache.data:
                    value = await excepts(func, catch_exception, mock(data))(
                        *args, **kwargs
                    )
                    update_cache_history(key, value, now)
                else:
                    cache.history[key].latest = now
                    cache.history[key].count += 1

                return cache.data[key]

        else:

            def wrapper(*args, **kwargs):
                now = timer()
                key = hash_generator(*args, **kwargs)
                data, _ = __check_and_remove_outdated(
                    hash_generator, cache, ttl, now, key
                )

                if key not in cache.data:
                    value = excepts(func, catch_exception, mock(data))(*args, **kwargs)
                    update_cache_history(key, value, now)
                else:
                    cache.history[key].latest = now
                    cache.history[key].count += 1

                return cache.data[key]

        def uncache(*args, **kwargs):
            cache.pop(hash_generator(*args, **kwargs))

        setattr(wrapper, "uncache", uncache)
        setattr(wrapper, "nocache", func)
        return functools.wraps(func)(wrapper)

    if _func:
        return decorator(_func)

    return decorator
