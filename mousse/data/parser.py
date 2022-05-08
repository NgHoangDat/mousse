from typing import *
from typing import _GenericAlias, _SpecialForm

from .dataclass import Dataclass
from .field import Field, get_fields_info
from .validator import validate

Generic = Union[_GenericAlias, _SpecialForm]

__all__ = ["Parser", "asdict", "asclass", "parse", "parser"]


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
        assert origin in parsers, f"No parser found for {origin}"

        parser = parsers[origin]
        return parser(G, obj)

    if G in parsers:
        parser = parsers[G]
        return parser(G, obj)

    if isinstance(obj, G):
        return obj

    if issubclass(G, Dataclass):
        assert isinstance(obj, dict), f"Unable to parse from {type(obj)} to {G}"
        return G(**obj)

    return G(obj)


@parser(Any)
def parse_any(G: Generic, obj: Any):
    return obj


@parser(type(None))
def parse_none(G: Generic, obj: Any):
    return None


@parser(List, Set, Sequence)
def parse_sequence(G: Generic, obj: Any):
    arg, *_ = get_args(G)
    origin = get_origin(G)

    assert validate(Iterable, obj), f"Object is not an iterable"
    return origin(parse(arg, elem) for elem in obj)


@parser(Tuple)
def parse_tuple(G: Generic, obj: Any):
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
        if isinstance(field.annotation, _GenericAlias):
            val = parse(get_origin(field.annotation), val)

        return val


class ClassParser(Parser):
    def __call__(self, val: Any, field: Field) -> Any:
        return parse(field.annotation, val)


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
        dictionary[key] = val

    return dictionary


def asclass(cls: Type[Dataclass], obj: Any, parser: Parser = ClassParser()):
    assert isinstance(obj, dict), f"Unable to convert {type(obj)} to {cls}"
    fields: Dict[str, Field] = get_fields_info(cls)

    alias = {}
    for key, field in fields.items():
        if field.alias is not None:
            alias[field.alias] = key

    obj = {alias.get(key, key): val for key, val in obj.items()}
    return cls(**{key: parser(val, fields[key]) for key, val in obj.items()})
