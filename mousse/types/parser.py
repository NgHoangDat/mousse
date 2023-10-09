import collections
import json
import os
from pathlib import Path
from typing import *

import yaml

from .dataclass import Dataclass
from .field import Field, get_fields_info
from .types import Generic, get_args, get_origin, is_generic
from .validator import validate

__all__ = ["Parser", "asdict", "asclass", "parse", "parser"]


def load_yaml(stream: Any) -> Dict[str, Any]:
    return yaml.load(stream, Loader=yaml.Loader) or {}


def dump_yaml(data: Any, stream: Any):
    return yaml.dump(
        data,
        stream,
        Dumper=yaml.Dumper,
        default_flow_style=False,
        indent=2,
        allow_unicode=True,
    )


LOADER = {".json": json.load, ".yaml": load_yaml, ".yml": load_yaml}

DUMPER = {".json": json.dump, ".yaml": dump_yaml, ".yml": dump_yaml}


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


def parse(G: Union[Generic, Type], obj: Any, **kwargs):
    if is_generic(G):
        origin = get_origin(G)
        if origin in parsers:
            parser = parsers[origin]
            return parser(G, obj, **kwargs)

    if G in parsers:
        parser = parsers[G]
        return parser(G, obj, **kwargs)

    if isinstance(obj, G):
        return obj

    if issubclass(G, Dataclass):
        return asclass(G, obj, **kwargs)

    if obj is Ellipsis:
        return G()

    if obj is None:
        return obj

    return G(obj)


@parser(Any)
def parse_any(G: Generic, obj: Any, **kwargs):
    return obj


@parser(type(None))
def parse_none(G: Generic, obj: Any, **kwargs):
    return None


@parser(List, Set, Sequence)
def parse_sequence(G: Generic, obj: Any, **kwargs):
    arg, *_ = get_args(G) + (Any,)
    origin = get_origin(G) or G
    if origin is collections.abc.Sequence:
        origin = list

    assert validate(Iterable, obj), f"Object is not an iterable"
    return origin(parse(arg, elem, **kwargs) for elem in obj)


@parser(Tuple)
def parse_tuple(G: Generic, obj: Any, **kwargs):
    if G is tuple:
        return tuple(obj)

    args = get_args(G)

    if len(args) == 1 and len(obj) > 1:
        assert False, f"Number of params mismatch"
    assert validate(Iterable, obj), f"Object is not an iterable"

    curr_idx = 0
    data = []
    for i, elem in enumerate(obj):
        data.append(parse(args[curr_idx], elem, **kwargs))

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
def parse_dict(G: Generic, obj: Any, **kwargs):
    assert issubclass(type(obj), Mapping), f"Unable to parse from {type(obj)} to {G}"
    if is_generic(G):
        key_type, val_type = get_args(G)
        return {
            parse(key_type, key, **kwargs): parse(val_type, val, **kwargs)
            for key, val in obj.items()
        }

    return {key: asdict(val, **kwargs) for key, val in obj.items()}


@parser(Union)
def parse_union(G: Generic, obj: Any, **kwargs):
    args = get_args(G)
    for arg in args:
        try:
            return parse(arg, obj, **kwargs)
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
    def __call__(self, val: Any, field: Field, **kwargs) -> Any:
        return val


class DictParser(Parser):
    def __call__(self, val: Any, field: Field, **kwargs):
        if val == Ellipsis:
            return val

        if isinstance(field.annotation, get_args(Generic)):
            if getattr(field.annotation, "_name", None) == "Dict":
                return parse(field.annotation, val, **kwargs)

            return parse(field.annotation, val, **kwargs)

        return val


class ClassParser(Parser):
    def __call__(self, val: Any, field: Field, **kwargs) -> Any:
        return parse(field.annotation, val, **kwargs)


def load(path: Union[str, Path]) -> Dict[str, Any]:
    if type(path) is not Path:
        path = Path(path).resolve()

    with open(path, encoding="utf-8") as fin:
        loader = LOADER.get(path.suffix.lower())
        if loader is None:
            raise Exception(f"file format {path.suffix} is not supported")

        params = loader(fin)

    return params


def dump(data: Any, path: Union[str, Path]):
    if type(path) is not Path:
        path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fout:
        dumper = DUMPER.get(path.suffix.lower())
        if dumper is None:
            raise Exception(f"file format {path.suffix} is not supported")

        dumper(data, fout)


def asdict(
    obj: Dataclass,
    by_alias: bool = True,
    path: Path = None,
    parser: Parser = DictParser(),
):

    data = None

    if isinstance(obj, (list, set, tuple)):
        data = type(obj)(asdict(elem, by_alias=by_alias, parser=parser) for elem in obj)

    elif not isinstance(obj, Dataclass):
        data = parse(type(obj), obj)

    else:
        fields: Dict[str, Field] = get_fields_info(type(obj), obj)
        data: Dict[str, Any] = {}

        for key, field in fields.items():
            if field.private:
                continue

            val = getattr(obj, key)
            val = parser(val, field, by_alias=by_alias)

            if isinstance(val, Dataclass):
                val = asdict(val, by_alias=by_alias, parser=parser)
            elif isinstance(val, (list, set, tuple)):
                val = type(val)(
                    asdict(elem, by_alias=by_alias, parser=parser) for elem in val
                )
            elif isinstance(val, dict):
                val = {
                    _key: asdict(_val, by_alias=True, parser=parser)
                    for _key, _val in val.items()
                }
            else:
                pass

            key = field.alias if by_alias and field.alias is not None else key
            if val != Ellipsis:
                data[key] = val

    if path is not None and data is not None:
        dump(data, path=path)

    return data


def asclass(
    cls: Type[Dataclass],
    obj: Any = None,
    path: Union[str, Path] = None,
    env: str = None,
    parser: Parser = ClassParser(),
):
    fields: Dict[str, Field] = get_fields_info(cls)
    alias = {}
    for key, field in fields.items():
        alias[field.alias if field.alias is not None else key] = key

    local_obj = obj or {}

    path_obj = {}
    if path is not None:
        if type(path) is not Path:
            path = Path(path).resolve()
        path_obj = load(path)

    env_obj = {}
    if env:
        for key, val in os.environ.items():
            if key.startswith(env + "_"):
                key = key[len(env) + 1 :]
                if key in alias:
                    key = alias[key]
                    env_obj[key] = val

    data = {**env_obj, **path_obj}
    if isinstance(local_obj, Dataclass):
        local_obj = asdict(local_obj)

    for key in local_obj:
        data[key] = local_obj[key]

    schema_data = {}
    custom_data = {}
    for key, val in data.items():
        if key in alias:
            key = alias[key]

        if key in fields:
            schema_data[key] = parser(val, fields[key])
            continue

        custom_data[key] = val

    data = {**custom_data, **schema_data}
    ins = cls(**data)
    return ins
