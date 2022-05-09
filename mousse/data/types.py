import sys

__all__ = ["Generic", "get_args", "get_origin"]

if sys.version_info > (3, 7):
    from typing import _GenericAlias, _SpecialForm, Union

    Generic = Union[_GenericAlias, _SpecialForm]
else:
    from typing import GenericMeta as Generic

    setattr(Generic, "__args__", (Generic,))


if sys.version_info > (3, 8):
    from typing import get_args, get_origin
else:

    def get_args(generic: Generic):
        return getattr(generic, "__args__", ())

    def get_origin(generic: Generic):
        return getattr(generic, "__origin__", None)
