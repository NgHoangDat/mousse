import asyncio
import io
import logging
import os
import time
from functools import lru_cache, wraps
from logging import Handler, StreamHandler
from logging.handlers import RotatingFileHandler
from typing import *
from typing import Callable

__all__ = ["init_logger", "get_logger", "log_error", "log_time", "add_handler"]


FORMATTER = logging.Formatter(
    "[%(asctime)s] [%(process)d %(thread)d] [%(levelname)s] [%(filename)s.%(funcName)s:%(lineno)i] %(message)s",
    "%Y-%m-%d %H:%M:%S",
)


class LoggerWrapper:
    def __init__(self, logger: logging.Logger = None) -> None:
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger()
            add_handler(self.logger, StreamHandler())

    def __gen_msg(self, *msg) -> str:
        buffer = io.StringIO()
        print(*msg, end="", file=buffer)
        msg = buffer.getvalue()
        return msg

    def info(self, *msg, stacklevel: int = 2, **kwargs) -> None:
        return self.logger.info(self.__gen_msg(*msg), stacklevel=stacklevel, **kwargs)

    def debug(self, *msg, stacklevel: int = 2, **kwargs) -> None:
        return self.logger.debug(self.__gen_msg(*msg), stacklevel=stacklevel, **kwargs)

    def error(self, *msg, stacklevel: int = 2, **kwargs) -> None:
        return self.logger.error(self.__gen_msg(*msg), stacklevel=stacklevel, **kwargs)

    def exception(self, *msg, stacklevel: int = 2, **kwargs) -> None:
        return self.logger.exception(
            self.__gen_msg(*msg), stacklevel=stacklevel, **kwargs
        )

    def critical(self, *msg, stacklevel: int = 2, **kwargs) -> None:
        return self.logger.critical(
            self.__gen_msg(*msg), stacklevel=stacklevel, **kwargs
        )

    def warning(self, *msg, stacklevel: int = 2, **kwargs) -> None:
        return self.logger.warning(
            self.__gen_msg(*msg), stacklevel=stacklevel, **kwargs
        )


@lru_cache(typed=True)
def get_logger(*args):
    return LoggerWrapper()


@lru_cache(typed=True)
def init_logger(
    name: str = "default",
    log_dir: Optional[str] = None,
    max_bytes: int = 10000000,
    backup_count: int = 5,
    level: int = logging.INFO,
) -> logging.Logger:    
    wrapper = get_logger(name)
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
                    logger.error(f"{func.__name__}: {e}", stacklevel=3)
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
                    logger.error(f"{func.__name__}: {e}", stacklevel=3)
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
                logger.info(f"{func.__name__}: {end - start}s", stacklevel=3)
                return res

        else:

            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.time()
                res = func(*args, **kwargs)
                end = time.time()
                logger.info(f"{func.__name__}: {end - start}s", stacklevel=3)
                return res

        return wrapper

    if _func:
        return decorator(_func)

    return decorator
