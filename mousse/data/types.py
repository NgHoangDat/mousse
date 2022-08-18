import sys

__all__ = ["Generic", "get_args", "get_origin", "is_generic"]

if sys.version_info > (3, 7):
    from typing import _GenericAlias, _SpecialForm, Union

    Generic = Union[_GenericAlias, _SpecialForm]
else:
    from typing import *
    from typing import GenericMeta as Generic

    setattr(Generic, "__args__", (Generic,))


if sys.version_info > (3, 8):
    from typing import get_args, get_origin
    
    def is_generic(generic: Generic):
        return isinstance(generic, get_args(Generic))
    
else:
    from typing import List, Set, Sequence, Tuple
    
    generic_mappings = {
        List: list, Set: set, Sequence: List, Tuple: tuple,
    }

    def is_generic(generic: Generic):
        origin = getattr(generic, "__origin__", None)
        if origin is Union:
            return True
        
        return isinstance(generic, get_args(Generic))

    def get_args(generic: Generic):
        return getattr(generic, "__args__", ())

    def get_origin(generic: Generic):
        origin = getattr(generic, "__origin__", None)
        if origin in generic_mappings:
            return generic_mappings[origin]

        if origin is None and is_generic(generic) and hasattr(generic, "mro"):
            for parent in generic.mro()[1:]:                
                return parent
            
        return origin
