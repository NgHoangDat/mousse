from abc import ABCMeta, abstractmethod
from collections import defaultdict
from typing import *

from ..types import Accessor, DataMetaclass

__all__ = ["Listener", "Mediator"]


class Listener(metaclass=ABCMeta):
    @abstractmethod
    def on_change(self, key: str, val: Any, mediator: "Mediator" = None):
        pass


class MediatorItemAccess(Accessor):
    def __set__(self, obj: "Mediator", value: Any):
        obj.notify(self.key)
        super().__set__(obj, value)


class MediatorMetaclass(DataMetaclass):
    def __new__(
        cls,
        name: str,
        bases: Tuple[type, ...],
        data: Dict[str, Any],
        accessor: Type[Accessor] = MediatorItemAccess,
    ):
        return super().__new__(cls, name, bases, data, accessor=accessor)


class Mediator(metaclass=MediatorMetaclass):
    def __new__(cls):
        instance = super().__new__(cls)
        instance.listeners = defaultdict(list)
        return instance

    def notify(self, key: str):
        unique_listeners = set()
        for listener in self.listeners[key]:
            unique_listeners.add(listener)

        for listener in self.listeners[""]:
            unique_listeners.add(listener)

        val = getattr(self, key)
        for listener in unique_listeners:
            listener.on_change(key, val, mediator=self)

    def add(self, listener: "Listener", *keys: List[str]):
        if len(keys) == 0:
            keys += ("",)

        for key in keys:
            self.listeners[key].append(listener)
