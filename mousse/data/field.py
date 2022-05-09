from functools import lru_cache
from typing import *


__all__ = ["Field", "get_fields_info"]


class Field:
    def __init__(
        self,
        default: Any = Ellipsis,
        alias: str = None,
        freeze: bool = False,
        exclude: bool = None,
    ) -> None:
        self.default = default
        self.alias = alias
        self.freeze = freeze
        self.annotation = None
        self.exclude = exclude


@lru_cache(typed=True)
def get_fields_info(cls: Any):
    return {}
