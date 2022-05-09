import asyncio
import json
import logging
import time
from copy import deepcopy
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from threading import Thread
from typing import *
from typing import Callable

from yaml import Loader, load

from ..data import parse, parser
from ..scheduler import call_after

NoneType = type(None)

__all__ = ["get_config", "load_config", "watch", "watch_async", "Config"]


def load_yaml(stream: Any) -> Dict[str, Any]:
    return load(stream, Loader=Loader) or {}


LOADER = {".json": json.load, ".yaml": load_yaml, ".yml": load_yaml}


class ConfigDetail(Mapping):
    def __iter__(self):
        for _ in range(0):
            yield _

    def __getitem__(self, key: str):
        return getattr(self, key)

    def __len__(self) -> int:
        return 0

    def __repr__(self):
        components = []
        for key in self:
            val = getattr(self, key)

            if type(val) is str:
                components.append(f'{key}="{val}"')
            else:
                components.append(f"{key}={val}")

        components = ", ".join(components)

        return f"Config({components})"


class ConfigDetailContainer:
    def __init__(self, freeze: bool = True):
        self.detail = ConfigDetail()
        self.freeze = freeze


class ConfigDetailAccessor:
    def __init__(self, val: Any):
        self.val = val

    def __get__(self, obj: Any, *args, **kwargs):
        return deepcopy(self.val)

    def __set__(self, obj: Any, val: Any):
        container = get_container(obj)
        assert not container.freeze, f"Permission denied"
        self.val = val


@lru_cache(typed=True)
def get_container(ins: Any):
    return ConfigDetailContainer()


class Config(Mapping):
    def __getattribute__(self, key: str):
        container = get_container(self)
        if hasattr(container.detail, key):
            return getattr(container.detail, key)

        return super().__getattribute__(key)

    def __setattr__(self, key: str, val: Any):
        container = get_container(self)
        if hasattr(container.detail, key):
            assert not container.freeze, f"Permission denied"
            return update(self, **{key: val})

        return super().__setattr__(key, val)

    def __iter__(self):
        container = get_container(self)
        for key in container.detail:
            yield key

    def __getitem__(self, key: str):
        container = get_container(self)
        return getattr(container.detail, key)

    def __len__(self) -> int:
        container = get_container(self)
        return len(container)

    def __hash__(self):
        return id(self)

    def __repr__(self):
        components = []
        for key in self:
            val = getattr(self, key)
            if type(val) is str:
                components.append(f'{key}="{val}"')
            else:
                components.append(f"{key}={val}")

        components = ", ".join(components)
        return f"Config({components})"


async def watch_async(
    config: Config,
    loop: asyncio.AbstractEventLoop,
    emitter: Callable,
    refresh: bool = True,
    logger: Optional[logging.Logger] = None,
    **timedetail,
):

    if not asyncio.iscoroutinefunction(emitter):
        emitter = asyncio.coroutine(emitter)

    @call_after(loop, repeated=refresh, **timedetail)
    async def observer(ignore_exception: bool = True):
        try:
            data = await emitter()
            update(config, **data)
        except Exception as e:
            if not ignore_exception:
                raise e

            if logger:
                logger.error(e)

    await observer(ignore_exception=False)
    observer.promise(ignore_exception=True)


def watch(
    config: Config,
    emitter: Callable,
    logger: Optional[logging.Logger] = None,
    **timedetail,
):
    timestamp = timedelta(**timedetail).total_seconds()

    def observer():
        while True:
            time.sleep(timestamp)
            try:
                update(config, **emitter())
            except Exception as e:
                if logger:
                    logger.error(e)

    update(config, **emitter())
    task = Thread(target=observer)
    task.daemon = True
    task.start()


def asdetail(obj: Any):
    if isinstance(obj, dict):
        data = {key: ConfigDetailAccessor(asdetail(val)) for key, val in obj.items()}

        def __iter__(self):
            for key in obj:
                yield key

        def __len__(self):
            return len(obj)

        data["__iter__"] = __iter__
        data["__len__"] = __len__

        return type("ConfigDetail", (ConfigDetail,), data)()

    if isinstance(obj, (list, set, tuple)):
        return tuple(asdetail(val) for val in obj)

    return obj


def update(config: Config, **kwargs):
    container = get_container(config)
    data = {}
    for key, val in kwargs.items():
        data[key] = asdetail(val)

    detail = container.detail

    def __iter__(self):
        for key in detail:
            yield key

        for key in kwargs:
            yield key

    def __len__(self):
        return len(detail) + len(kwargs)

    data["__iter__"] = __iter__
    data["__len__"] = __len__

    container.detail = type("ConfigDetail", (type(detail),), data)()


def freeze(config: Config):
    container = get_container(config)
    container.freeze = True


def unfreeze(config: Config):
    container = get_container(config)
    container.freeze = False


@parser(Config)
def parse_config(G: Type[Config], config: Config):
    data = {}
    for key in config:
        val = getattr(config, key)
        val_type = type(val)
        if issubclass(val_type, ConfigDetail):
            val = parse(Config, val)
        else:
            if issubclass(val_type, (list, tuple, set)):
                val = parse(List[Union[Config, Any]], val)

            val = parse(val_type, val)

        data[key] = val

    return data


@lru_cache(typed=True)
def get_config(*args, **kwargs):
    return Config()


@lru_cache(typed=True)
def load_config(*args, path: Union[str, Path, NoneType] = None, **kwargs):
    params = {}

    if path:
        if type(path) is str:
            path = Path(path)

        with open(path, encoding="utf-8") as f:
            loader = LOADER.get(path.suffix)
            if loader is None:
                raise Exception(f"file format {path.suffix} is not supported")

            params = loader(f)

    config = get_config(*args, **kwargs)
    update(config, **params)

    return config
