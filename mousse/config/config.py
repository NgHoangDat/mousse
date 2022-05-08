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

from ..data import parser, parse
from ..scheduler import call_after

NoneType = type(None)

__all__ = ["get_config", "load_config", "Config"]


def load_yaml(stream: Any) -> Dict[str, Any]:
    return load(stream, Loader=Loader) or {}


LOADER = {".json": json.load, ".yaml": load_yaml, ".yml": load_yaml}


class ConfigDetail:
    def __iter__(self):
        for _ in range(0):
            yield _


class ConfigDetailContainer:
    def __init__(self, freeze: bool = True):
        self.detail = ConfigDetail()
        self.freeze = freeze


class ConfigDetailAccessor:
    def __init__(self, val: Any):
        self.val = val

    def __get__(self, obj: Any, *args, **kwargs):
        return deepcopy(self.val)


@lru_cache(typed=True)
def get_container(ins: Any):
    return ConfigDetailContainer()


class Config:
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
        for item in container.detail:
            yield item

    async def watch_async(
        self,
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
                update(self, **data)
            except Exception as e:
                if not ignore_exception:
                    raise e

                if logger:
                    logger.error(e)

        await observer(ignore_exception=False)
        observer.promise(ignore_exception=True)

    def watch(
        self,
        emitter: Callable,
        logger: Optional[logging.Logger] = None,
        **timedetail,
    ):
        timestamp = timedelta(**timedetail).total_seconds()

        def observer():
            while True:
                time.sleep(timestamp)
                try:
                    update(self, **emitter())
                except Exception as e:
                    if logger:
                        logger.error(e)

        update(self, **emitter())
        task = Thread(target=observer)
        task.daemon = True
        task.start()


def asdetail(obj: Any):
    if isinstance(obj, dict):
        data = {key: asdetail(val) for key, val in obj.items()}

        def __iter__(self):
            for key in obj:
                yield key, getattr(self, key)

        data["__iter__"] = __iter__

        return type("ConfigDetail", (ConfigDetail,), data)()

    return ConfigDetailAccessor(obj)


def update(config: Config, **kwargs):
    container = get_container(config)
    data = {}
    for key, val in kwargs.items():
        data[key] = asdetail(val)

    detail = container.detail

    def __iter__(self):
        for key in detail:
            yield key, getattr(detail, key)

        for key in kwargs:
            yield key, getattr(self, key)

    data["__iter__"] = __iter__
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
    for key, val in config:
        val_type = type(val)
        if issubclass(val_type, ConfigDetail):
            val = parse(Config, val)
        else:
            val = parse(val_type, val)

        data[key] = val

    return data


@lru_cache(typed=True)
def get_config(*args, **kwargs):
    return Config()


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
