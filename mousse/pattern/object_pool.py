from collections import OrderedDict
from typing import *

__all__ = ["ObjectPool", "object_pool"]


class ObjectPool(type):
    def __new__(cls, name: str, bases: Tuple[type, ...], data: Dict[str, Any]):
        new_bases = []
        for base in bases:
            if hasattr(base, "object_cls"):
                object_cls = getattr(base, "object_cls")
                if object_cls:
                    new_bases.append(object_cls)
            else:
                new_bases.append(base)

        bases = tuple(new_bases)
        core = super().__new__(cls, name, bases, data)

        wrapper_data = {}

        def register(func):
            wrapper_data[func.__name__] = classmethod(func)
            return func

        @register
        def get(cls, key: Hashable) -> Type[core]:
            return cls.instances[key]

        @register
        def new(cls, *args, **kwargs):
            return cls.object_cls(*args, **kwargs)

        @register
        def set(cls, key: Hashable, val: Type[core]):
            cls.instances[key] = val

        @register
        def pop(cls, key: Hashable) -> Type[core]:
            val = cls.instances[key]
            del cls.instances
            return val

        @register
        def keys(cls):
            return cls.instances.keys()

        @register
        def values(cls):
            return cls.instances.values()

        @register
        def items(cls):
            return cls.instances.items()

        @register
        def clear(cls):
            cls.instances.clear()

        @register
        def has(cls, key: Hashable):
            return key in cls.instances

        @register
        def size(cls):
            return len(cls.instances)

        wrapper = super().__new__(cls, name, (), wrapper_data)

        wrapper.object_cls = core
        wrapper.instances = OrderedDict()

        return wrapper

    def __instancecheck__(self, instance: Any):
        if hasattr(self, "object_cls"):
            return isinstance(instance, self.object_cls)
        return False

    def __subclasscheck__(self, instance: Any):
        for cls in instance.object_cls.mro():
            if cls == self.object_cls:
                return True
        return False


def object_pool(cls: Any):
    return ObjectPool(cls.__name__, (cls,), {})
