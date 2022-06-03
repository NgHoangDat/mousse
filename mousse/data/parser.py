import collections
import json
from pathlib import Path
from typing import *

import yaml

from .dataclass import Dataclass
from .field import Field, get_fields_info
from .types import Generic, get_args, get_origin
from .validator import validate

__all__ = ["Parser", "asdict", "asclass", "parse", "parser"]


def load_yaml(stream: Any) -> Dict[str, Any]:
    return yaml.load(stream, Loader=yaml.Loader) or {}


LOADER = {".json": json.load, ".yaml": load_yaml, ".yml": load_yaml}


parsers = {}


def parser(*types: Type[Generic], func: Callable = None):
    def decorator(func: Callable):
        for _type in types:
            origin = get_origin(_type)
            if origin is None:
                origin = _type

            parsers[origin] = func
        return func

    if func is not None:
        return decorator(func)

    return decorator


def parse(G: Union[Generic, Type], obj: Any):
    if isinstance(G, get_args(Generic)):
        origin = get_origin(G)
        if origin in parsers:
            parser = parsers[origin]
            return parser(G, obj)

    if G in parsers:
        parser = parsers[G]
        return parser(G, obj)

    if isinstance(obj, G):
        return obj

    if issubclass(G, Dataclass):
        return asclass(G, obj)

    if obj is Ellipsis:
        return G()

    if obj is None:
        return obj

    return G(obj)


@parser(Any)
def parse_any(G: Generic, obj: Any):
    return obj


@parser(type(None))
def parse_none(G: Generic, obj: Any):
    return None


@parser(List, Set, Sequence)
def parse_sequence(G: Generic, obj: Any):
    arg, *_ = get_args(G) + (Any,)
    origin = get_origin(G) or G
    if origin is collections.abc.Sequence:
        origin = list

    assert validate(Iterable, obj), f"Object is not an iterable"
    return origin(parse(arg, elem) for elem in obj)


@parser(Tuple)
def parse_tuple(G: Generic, obj: Any):
    if G is tuple:
        return tuple(obj)

    args = get_args(G)

    if len(args) == 1 and len(obj) > 1:
        assert False, f"Number of params mismatch"
    assert validate(Iterable, obj), f"Object is not an iterable"

    curr_idx = 0
    data = []
    for i, elem in enumerate(obj):
        data.append(parse(args[curr_idx], elem))

        if i < len(obj) - 1:
            if curr_idx + 1 < len(args):
                if args[curr_idx + 1] != Ellipsis:
                    curr_idx += 1
                continue

            assert False, f"Number of params mismatch"

    if curr_idx + 1 < len(args) and args[curr_idx + 1] != Ellipsis:
        assert False, f"Number of params mismatch"

    return tuple(data)


@parser(Dict)
def parse_dict(G: Generic, obj: Any):
    assert issubclass(type(obj), dict), f"Unable to parse from {type(obj)} to {G}"
    key_type, val_type = get_args(G)
    return {parse(key_type, key): parse(val_type, val) for key, val in obj.items()}


@parser(Union)
def parse_union(G: Generic, obj: Any):
    args = get_args(G)
    for arg in args:
        try:
            return parse(arg, obj)
        except Exception as e:
            continue

    assert False, f"Unable to parse from {type(obj)} to {G}"


class ParserMetaclass(type):
    def __new__(
        cls: Type,
        name: str,
        bases: Tuple[Type, ...],
        data: Dict[str, Any],
        **kwargs,
    ):
        return super().__new__(cls, name, bases, data)


class Parser(metaclass=ParserMetaclass):
    def __call__(self, val: Any, field: Field) -> Any:
        return val


class DictParser(Parser):
    def __call__(self, val: Any, field: Field):
        if val == Ellipsis:
            return val

        if isinstance(field.annotation, get_args(Generic)):
            if getattr(field.annotation, "_name", None) == "Dict":
                return parse(field.annotation, val)

            return parse(get_origin(field.annotation), val)

        return val


class ClassParser(Parser):
    def __call__(self, val: Any, field: Field) -> Any:
        return parse(field.annotation, val)


def load(path: Union[str, Path]) -> Dict[str, Any]:
    if type(path) is not Path:
        path = Path(path).resolve()

    with open(path, encoding="utf-8") as f:
        loader = LOADER.get(path.suffix)
        if loader is None:
            raise Exception(f"file format {path.suffix} is not supported")

        params = loader(f)

    return params


def asdict(obj: Dataclass, by_alias: bool = True, parser: Parser = DictParser()):
    if not isinstance(obj, Dataclass):
        return parse(type(obj), obj)

    fields: Dict[str, Field] = get_fields_info(type(obj))
    dictionary: Dict[str, Any] = {}
    for key, field in fields.items():
        if field.exclude:
            continue

        val = getattr(obj, key)
        if isinstance(val, Dataclass):
            val = asdict(val, by_alias=by_alias, parser=parser)
        elif isinstance(obj, (list, set, tuple)):
            val = type(val)(asdict(elem) for elem in val)
        elif isinstance(obj, dict):
            val = {_key: asdict(_val) for _key, _val in val.items()}
        else:
            pass

        val = parser(val, field)

        key = field.alias if by_alias and field.alias is not None else key
        if val != Ellipsis:
            dictionary[key] = val

    return dictionary


def asclass(
    cls: Type[Dataclass],
    obj: Any = None,
    path: Union[str, Path] = None,
    parser: Parser = ClassParser(),
):
    assert (obj is not None) ^ (path is not None), f"Only use obj or path at once"

    if path is not None:
        if type(path) is not Path:
            path = Path(path).resolve()
            obj = load(path)

    assert issubclass(type(obj), Mapping), f"Unable to convert {type(obj)} to {cls}"
    fields: Dict[str, Field] = get_fields_info(cls)

    alias = {}
    for key, field in fields.items():
        if field.alias is not None:
            alias[field.alias] = key

    data = {**obj}
    data = {
        alias.get(key, key): val
        for key, val in data.items()
        if alias.get(key, key) in fields
    }

    return cls(**{key: parser(val, fields[key]) for key, val in data.items()})
