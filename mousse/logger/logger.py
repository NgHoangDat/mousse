import asyncio
import inspect
import io
import logging
import os
import time
from functools import lru_cache, wraps
from logging import Handler, StreamHandler
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import *
from typing import Callable

__all__ = ["init_logger", "get_logger", "log_error", "log_time", "add_handler"]


FORMATTER = logging.Formatter(
    "[%(asctime)s] [%(process)d %(thread)d] [%(levelname)s] %(message)s",
    "%Y-%m-%d %H:%M:%S",
)


class LoggerWrapper:
    def __init__(self, logger: logging.Logger = None) -> None:
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger()
            add_handler(self.logger, StreamHandler())

    def __gen_msg(self, *msg, stack_level: int = 1) -> str:
        buffer = io.StringIO()
        print(*msg, end="", file=buffer)
        msg = buffer.getvalue()

        frame = inspect.currentframe()
        caller = frame.f_back
        for _ in range(stack_level - 1):
            f_prev = caller.f_back
            if f_prev is not None:
                caller = f_prev

        filepath = Path(caller.f_code.co_filename)
        filename = f"{filepath.parent}/{filepath.stem}"

        extra = {
            "filename": filename,
            "lineno": caller.f_lineno,
            "func": caller.f_code.co_name,
        }

        msg = "[{filename}:{func}:{lineno}] {msg}".format(msg=msg, **extra)
        return msg

    def info(self, *msg, stack_level: int = 2, **kwargs) -> None:
        return self.logger.info(self.__gen_msg(*msg, stack_level=stack_level), **kwargs)

    def debug(self, *msg, stack_level: int = 2, **kwargs) -> None:
        return self.logger.debug(
            self.__gen_msg(*msg, stack_level=stack_level), **kwargs
        )

    def error(self, *msg, stack_level: int = 2, **kwargs) -> None:
        return self.logger.error(
            self.__gen_msg(*msg, stack_level=stack_level), **kwargs
        )

    def exception(self, *msg, stack_level: int = 2, **kwargs) -> None:
        return self.logger.exception(
            self.__gen_msg(*msg, stack_level=stack_level), **kwargs
        )

    def critical(self, *msg, stack_level: int = 2, **kwargs) -> None:
        return self.logger.critical(
            self.__gen_msg(*msg, stack_level=stack_level), **kwargs
        )

    def warning(self, *msg, stack_level: int = 2, **kwargs) -> None:
        return self.logger.warning(
            self.__gen_msg(*msg, stack_level=stack_level), **kwargs
        )


@lru_cache(typed=True)
def __get_logger(name: str) -> LoggerWrapper:
    return LoggerWrapper()


def get_logger(name: str = "default") -> LoggerWrapper:
    return __get_logger(name)


@lru_cache(typed=True)
def __init_logger(
    name: str, log_dir: str, max_bytes: int, backup_count: int, level: int
) -> LoggerWrapper:
    wrapper = get_logger(name=name)
    logger = wrapper.logger
    logger.setLevel(level)

    if log_dir is not None:
        os.makedirs(log_dir, exist_ok=True)
        log_filename = os.path.join(log_dir, f"{name}.out")
        add_handler(
            logger,
            RotatingFileHandler(
                log_filename, maxBytes=max_bytes, backupCount=backup_count
            ),
        )

    return wrapper


def init_logger(
    name: str = "default",
    log_dir: Optional[str] = None,
    max_bytes: int = 10000000,
    backup_count: int = 5,
    level: int = logging.INFO,
) -> LoggerWrapper:
    return __init_logger(name, log_dir, max_bytes, backup_count, level)


def add_handler(
    logger: logging.Logger,
    *handlers: List[Handler],
    formatter: logging.Formatter = FORMATTER,
):
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)


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
