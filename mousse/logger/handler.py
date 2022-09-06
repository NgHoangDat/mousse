import logging
import uuid
from datetime import datetime
from logging import Handler as BaseHandler
from logging import handlers
from pathlib import Path
from typing import *

from ..pattern import AutoRegistry, Registry

__all__ = ["Handler", "handler_registry"]


REGISTRY = uuid.uuid1()
handler_registry = Registry.get(REGISTRY)


class Handler(BaseHandler, metaclass=AutoRegistry, registry=REGISTRY):
    def setLevel(self, level: int) -> "Handler":
        super().setLevel(level)
        return self

    def setFormatter(self, formatter: logging.Formatter) -> "Handler":
        super().setFormatter(formatter)
        return self


class RotatingFileHandler(handlers.RotatingFileHandler, Handler):
    def __init__(
        self,
        path: str,
        mode: str = "a",
        max_bytes: int = 1e7,
        backup_count: int = 5,
        encoding: Union[str, None] = None,
        delay: bool = False,
        **kwargs,
    ) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(
            path.as_posix(), mode, max_bytes, backup_count, encoding, delay
        )


class TimedRotatingFileHandler(handlers.TimedRotatingFileHandler, Handler):
    def __init__(
        self,
        path: str,
        when: str = "h",
        interval: int = 1,
        backup_count: int = 0,
        encoding: Union[str, None] = None,
        delay: bool = False,
        utc: bool = False,
        at: Union[datetime.time, None] = None,
    ) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        super().__init__(
            path.as_posix(), when, interval, backup_count, encoding, delay, utc, at
        )


class QueueHandler(handlers.QueueHandler, Handler):
    pass


class BufferingHanlder(handlers.BufferingHandler, Handler):
    pass
