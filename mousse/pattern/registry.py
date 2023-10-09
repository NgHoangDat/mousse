from functools import partial
from typing import *

__all__ = ["Registry", "AutoRegistry", "register"]


class Registry:
    __GLOBAl_REGISTRIES: Dict[str, "Registry"] = {}

    def __init__(self, attr_name: str = "__name__"):
        self.registry = {}
        self.attr_name = attr_name

    def register(self, target: Any = None, key: str = None, overwrite: bool = False):
        def decorator(_target: Any, key: str = None, overwrite: bool = False):
            if key is None:
                key = getattr(_target, self.attr_name)

            assert (
                overwrite or key not in self.registry
            ), f"Duplicated key {key} found in registry"
            self.registry[key] = _target
            return _target

        if target is not None:
            return decorator(target, key=key, overwrite=overwrite)

        return partial(decorator, key=key, overwrite=overwrite)

    def __call__(self, key: str, *args, **kwargs):
        return self[key](*args, **kwargs)

    def __getitem__(self, key: str):
        assert key in self.registry, f"{key} not found in registry"
        return self.registry[key]

    def keys(self):
        return self.registry.keys()

    def values(self):
        return self.registry.values()

    def items(self):
        return self.registry.items()

    @classmethod
    def get(cls, key: str):
        if key not in cls.__GLOBAl_REGISTRIES:
            cls.set(key, cls())
        return cls.__GLOBAl_REGISTRIES[key]

    @classmethod
    def set(cls, key: str, registry: "Registry"):
        cls.__GLOBAl_REGISTRIES[key] = registry

    @classmethod
    def prepare(cls, key: str, *args, **kwargs):
        registry = cls(*args, **kwargs)
        cls.set(key, registry)


class AutoRegistry(type):
    def __new__(
        cls: Type,
        name: str,
        bases: Tuple[Type, ...],
        namespace: Dict[str, Any],
        registry: str = None,
        overwrite: bool = False,
        **kwargs,
    ):
        new_cls = super().__new__(cls, name, bases, namespace)
        if registry is None:
            for base in bases:
                if hasattr(base, "__REGISTRY__"):
                    registry = getattr(base, "__REGISTRY__")
                    break

        if not isinstance(registry, Registry):
            registry = Registry.get(registry)

        registry.register(target=new_cls, overwrite=overwrite)
        setattr(new_cls, "__REGISTRY__", registry)

        return new_cls


def register(name: str, target: Any = None, key: str = None, overwrite: bool = False):
    def decorator(_target: Any, key: str = None, overwrite: bool = False):
        registry = Registry.get(name)
        registry.register(target=_target, key=key, overwrite=overwrite)
        return _target

    if target is not None:
        return decorator(target, key=key, overwrite=overwrite)

    return partial(decorator, key=key, overwrite=overwrite)
