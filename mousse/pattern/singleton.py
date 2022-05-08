from typing import *

__all__ = ["Singleton", "singleton"]


class Singleton(type):
    def __new__(cls, name: str, bases: Tuple[type, ...], data: Dict[str, Any]):
        core_bases = []
        for base in bases:
            if hasattr(base, "object_cls"):
                object_cls = getattr(base, "object_cls")
                if object_cls:
                    core_bases.append(object_cls)
            else:
                core_bases.append(base)

        bases = tuple(core_bases)
        core = super().__new__(cls, name, bases, data)

        def get(cls):
            return cls.instance

        def init(cls, *args, **kwargs):
            cls.instance = cls.object_cls(*args, **kwargs)

        wrapper = super().__new__(
            cls,
            name,
            (),
            {
                "get": classmethod(get),
                "init": classmethod(init),
            },
        )

        wrapper.object_cls = core
        wrapper.instance = None

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


def singleton(cls: Type):
    return Singleton(cls.__name__, (cls,), {})
