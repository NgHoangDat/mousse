import asyncio
import json
import logging
import time
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from threading import Thread
from typing import *
from typing import Callable

from dialga import call_after
from yaml import Loader, load

from .accessor import Accessor
from .dataclass import Dataclass
from .parser import asclass, parse, parser

NoneType = type(None)

__all__ = ["get_config", "load_config", "watch", "watch_async", "Config"]


def load_yaml(stream: Any) -> Dict[str, Any]:
    return load(stream, Loader=Loader) or {}


LOADER = {".json": json.load, ".yaml": load_yaml, ".yml": load_yaml}


class ReadOnlyFieldException(Exception):
    def __init__(self, key: str):
        super().__init__(f"Field `{key}` is readonly")


class ConfigMetadata(Dataclass, dynamic=True):
    readonly: bool = False


class ConfigAccessor(Accessor):
    def __set__(self, obj: Any, val: Any):
        metadata = _get_metadata(obj, self.key)

        if metadata.readonly:
            raise ReadOnlyFieldException(self.key)

        metadata.readonly = True
        self.val = parse(Config, val)

    def __get__(self, obj: Any):
        return self.val


class Config(Dataclass, dynamic=True, accessor=ConfigAccessor):
    pass


@lru_cache(maxsize=None)
def _get_metadata(obj: Any, key: str) -> ConfigMetadata:
    return ConfigMetadata()


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


def update(config: Config, **kwargs):
    for key, val in kwargs.items():
        setattr(config, key, val)


def freeze(config: Any):
    if isinstance(config, tuple):
        for elem in config:
            freeze(elem)
        return

    if isinstance(config, Config):
        for key, val in config:
            metadata = _get_metadata(config, key)
            metadata.readonly = True
            freeze(val)


def unfreeze(config: Any):
    if isinstance(config, tuple):
        for elem in config:
            unfreeze(elem)
        return

    if isinstance(config, Config):
        for key, val in config:
            metadata = _get_metadata(config, key)
            metadata.readonly = False
            unfreeze(val)


@parser(Config)
def parse_config(G: Type[Config], config: Union[Mapping, list, tuple, set]):
    if isinstance(config, (list, tuple, set)):
        return tuple(parse_config(G, elem) for elem in config)

    if isinstance(config, Mapping):
        data = {}
        for key, val in config.items():
            val = parse_config(Config, val)
            data[key] = val

        return Config(**data)

    return config


@lru_cache(typed=True)
def __get_config(key: str):
    return Config()


def get_config(key: str):
    return __get_config(key)


@lru_cache(typed=True)
def __load_config(key: str, path: Union[str, Path, NoneType] = None):
    params = {}

    if path:
        if type(path) is str:
            path = Path(path)

        with open(path, encoding="utf-8") as f:
            loader = LOADER.get(path.suffix)
            if loader is None:
                raise Exception(f"file format {path.suffix} is not supported")

            params = loader(f)

    if key is not None:
        config = get_config(key)
    else:
        config = Config()

    update(config, **params)
    return config


def load_config(
    key: str = "default",
    path: Union[str, Path, NoneType] = None,
    schema: Dataclass = None,
    **kwargs,
):
    config = __load_config(key, path=path)
    if schema is not None:
        config = asclass(schema, config)
    return config
