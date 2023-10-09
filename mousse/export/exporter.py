from functools import lru_cache
from importlib import import_module
from inspect import currentframe, getmembers, getmodule, getouterframes, isclass
from pathlib import Path
from typing import Any, Callable, Dict

__all__ = ["export", "export_subclass", "export_instance"]


@lru_cache(maxsize=1)
def __get_cache():
    return {}


def export(
    predicate: Callable[[Any], bool],
    idx: int = 1,
    module: Any = None,
    package: str = None,
    registry: Dict[str, Any] = None,
) -> Dict[str, Any]:
    if registry is None:
        registry = {}

    curr_frame = currentframe()
    outer_frames = getouterframes(curr_frame)
    call_frame = outer_frames[idx]

    _globals = call_frame.frame.f_globals
    if "__all__" not in _globals:
        _globals["__all__"] = []

    __all = _globals["__all__"]

    if call_frame.function == "<module>":
        _locals = call_frame.frame.f_locals
    else:
        _locals = vars(getmodule(call_frame.frame))

    current_file = Path(_globals["__file__"]).resolve()
    current_dir = current_file.parent

    if package is None:
        package = _locals["__name__"]

    cached = __get_cache()
    unique_key = (module, package)

    if unique_key in cached:
        members = cached[unique_key]
    else:
        members = []
        for fn in current_dir.rglob("*.py"):
            path = fn.relative_to(current_dir).as_posix()[:-3]
            if path.startswith("__init__"):
                continue

            target = module or import_module(
                "." + path.replace("/", "."), package=package
            )

            members.extend(getmembers(target, predicate=predicate))

        cached[unique_key] = members

    for name, cls in members:
        if name not in _locals or name not in __all:
            _locals[name] = cls
            __all.append(name)

            registry[name] = cls

    return registry


def export_subclass(
    *classes, module: Any = None, package: str = None, registry: Dict[str, Any] = None
) -> Dict[str, Any]:
    predicate = lambda cls: isclass(cls) and issubclass(cls, classes)
    return export(predicate, idx=2, module=module, package=package, registry=registry)


def export_instance(
    *classes, module: Any = None, package: str = None, registry: Dict[str, Any] = None
) -> Dict[str, Any]:
    predicate = lambda ins: isinstance(ins, classes)
    return export(predicate, idx=2, module=module, package=package, registry=registry)
