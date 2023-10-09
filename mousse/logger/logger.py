import asyncio
import inspect
import io
import logging
import os
import time
from functools import lru_cache, wraps
from logging import StreamHandler
from pathlib import Path
from typing import *
from typing import Callable

from ..types import Dataclass, asclass, asdict, load_config
from .handler import Handler, handler_registry

__all__ = ["get_logger", "log_error", "log_time"]


DEFAULT_FMT = "[%(asctime)s] [%(process)d %(thread)d] [%(levelname)s] %(message)s"
DEFAULT_DATE_FMT = "%Y-%m-%d %H:%M:%S"


DEFAULT_FORMATTER = logging.Formatter(
    DEFAULT_FMT,
    DEFAULT_DATE_FMT,
)


class InvalidLoggerConfigException(Exception):
    pass


class FormatterConfig(Dataclass):
    fmt: str = DEFAULT_FMT
    datefmt: str = DEFAULT_DATE_FMT
    style: str = "%"
    validate: bool = True


class HandlerConfig(Dataclass):
    type: str
    level: int = logging.INFO
    params: Dict[str, Any] = {}
    formatter: FormatterConfig = FormatterConfig()


class LoggerConfig(Dataclass):
    level: int = logging.INFO
    include_extra: bool = True
    formatter: FormatterConfig = FormatterConfig()
    handlers: List[HandlerConfig] = []


class LoggerWrapper:
    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)

        self.handler = StreamHandler()
        self.logger.addHandler(self.handler)

        self.set_level(logging.INFO)
        self.set_formatter(DEFAULT_FORMATTER)

        self.include_extra = True

    def load_config(self, path: Union[str, Path]):
        try:
            config: LoggerConfig = load_config(None, path=path, schema=LoggerConfig)
        except Exception as e:
            raise InvalidLoggerConfigException("Logger config is invalid")

        self.set_level(config.level)
        self.set_formatter(logging.Formatter(**asdict(config.formatter)))

        for handler in config.handlers:
            formatter = logging.Formatter(**asdict(handler.formatter))
            self.add_handler(handler.type, **handler.params).setLevel(
                handler.level
            ).setFormatter(formatter)

        self.include_extra = config.include_extra

    def set_level(self, level: int) -> "LoggerWrapper":
        self.handler.setLevel(level)
        return self

    def set_formatter(self, formatter: logging.Formatter) -> "LoggerWrapper":
        self.handler.setFormatter(formatter)
        return self

    def add_handler(
        self,
        __handler: str,
        *args,
        **kwargs,
    ):
        handler: Handler = handler_registry(__handler, *args, **kwargs)
        handler.setFormatter(DEFAULT_FORMATTER)
        self.logger.addHandler(handler)
        return handler

    def __gen_msg(self, *msg, stack_level: int = 1, include_extra: bool = None) -> str:
        buffer = io.StringIO()
        print(*msg, end="", file=buffer)
        msg = buffer.getvalue()

        include_extra = (
            include_extra if include_extra is not None else self.include_extra
        )
        if include_extra:
            frame = inspect.currentframe()
            caller = frame.f_back
            for _ in range(stack_level - 1):
                f_prev = caller.f_back
                if f_prev is not None:
                    caller = f_prev

            cwd_path = Path(os.getcwd())
            filepath = Path(caller.f_code.co_filename).resolve()
            try:
                filepath = filepath.relative_to(cwd_path)
            except ValueError:
                pass

            filename = f"{filepath.parent}/{filepath.stem}"

            extra = {
                "filename": filename,
                "lineno": caller.f_lineno,
                "func": caller.f_code.co_name,
            }
            msg = "[{filename}:{func}:{lineno}] {msg}".format(msg=msg, **extra)

        return msg

    def info(
        self, *msg, stack_level: int = 2, include_extra: bool = None, **kwargs
    ) -> None:
        return self.logger.info(
            self.__gen_msg(*msg, stack_level=stack_level, include_extra=include_extra),
            **kwargs,
        )

    def debug(
        self, *msg, stack_level: int = 2, include_extra: bool = None, **kwargs
    ) -> None:
        return self.logger.debug(
            self.__gen_msg(*msg, stack_level=stack_level, include_extra=include_extra),
            **kwargs,
        )

    def error(
        self, *msg, stack_level: int = 2, include_extra: bool = None, **kwargs
    ) -> None:
        return self.logger.error(
            self.__gen_msg(*msg, stack_level=stack_level, include_extra=include_extra),
            **kwargs,
        )

    def exception(
        self, *msg, stack_level: int = 2, include_extra: bool = None, **kwargs
    ) -> None:
        return self.logger.exception(
            self.__gen_msg(*msg, stack_level=stack_level, include_extra=include_extra),
            **kwargs,
        )

    def critical(
        self, *msg, stack_level: int = 2, include_extra: bool = None, **kwargs
    ) -> None:
        return self.logger.critical(
            self.__gen_msg(*msg, stack_level=stack_level, include_extra=include_extra),
            **kwargs,
        )

    def warning(
        self, *msg, stack_level: int = 2, include_extra: bool = None, **kwargs
    ) -> None:
        return self.logger.warning(
            self.__gen_msg(*msg, stack_level=stack_level, include_extra=include_extra),
            **kwargs,
        )

    def enable_extra(self):
        self.include_extra = True

    def disable_extra(self):
        self.include_extra = False


@lru_cache(typed=True)
def __get_logger(name: str) -> LoggerWrapper:
    return LoggerWrapper(name)


def get_logger(name: str = "default") -> LoggerWrapper:
    return __get_logger(name)


def log_error(
    _func: Optional[Callable] = None,
    logger: Optional[logging.Logger] = None,
    return_value: Any = None,
    swallow_err: bool = False,
    **options,
):

    if logger is None:
        logger = logging.getLogger()

    if not isinstance(logger, LoggerWrapper):
        logger = LoggerWrapper(logger)

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    res = await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"{func.__name__}: {e}", stack_level=3)
                    if swallow_err:
                        return return_value
                    else:
                        raise e
                else:
                    return res

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    res = func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"{func.__name__}: {e}", stack_level=3)
                    if swallow_err:
                        return return_value
                    else:
                        raise e
                else:
                    return res

        return wrapper

    if _func:
        return decorator(_func)

    return decorator


def log_time(
    _func: Optional[Callable] = None, logger: Optional[logging.Logger] = None, **options
):

    if logger is None:
        logger = logging.getLogger()

    if not isinstance(logger, LoggerWrapper):
        logger = LoggerWrapper(logger)

    def decorator(func: callable):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.time()
                res = await func(*args, **kwargs)
                end = time.time()
                logger.info(f"{func.__name__}: {end - start}s", stack_level=3)
                return res

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                res = func(*args, **kwargs)
                end = time.time()
                logger.info(f"{func.__name__}: {end - start}s", stack_level=3)
                return res

        return wrapper

    if _func:
        return decorator(_func)

    return decorator
