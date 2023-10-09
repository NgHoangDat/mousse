import inspect
from abc import ABCMeta, abstractmethod
from copy import deepcopy
from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import *


@dataclass
class BasePlugin(metaclass=ABCMeta):
    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    def __post_init__(self):
        sig = inspect.signature(self.run)
        setattr(self, "__signature__", sig)

    def __call__(self, *args, **kwargs):
        curr_sig = inspect.signature(self.run)
        empty_default_vars = [
            param
            for param in curr_sig.parameters.values()
            if param.default == inspect._empty and param.kind < 2
        ]

        if len(empty_default_vars) <= len(args):
            return self.run(*args, **kwargs)

        def run(_, *nargs, **nkwargs):
            nargs = args + nargs
            kwargs.update(nkwargs)
            return self.run(*nargs, **kwargs)

        parameters = list(curr_sig.parameters.values())
        parameters = [Parameter("__self__", kind=0)]
        curr_parameters = list(curr_sig.parameters.items())[
            min(len(empty_default_vars), len(args)) :
        ]
        for name, param in curr_parameters:
            if name in kwargs:
                param = param.replace(default=kwargs[name])
            parameters.append(param)

        setattr(
            run,
            "__signature__",
            Signature(
                parameters=parameters, return_annotation=curr_sig.return_annotation
            ),
        )
        _dict = deepcopy(self.__dict__)
        _dict["run"] = run

        return type("Plugin", (BasePlugin,), _dict)()

    def __rshift__(self, step: "BasePlugin") -> "BasePlugin":
        curr_sig = inspect.signature(self)
        next_sig = inspect.signature(step)

        empty_default_args = [
            param
            for param in next_sig.parameters.values()
            if param.default == inspect._empty and param.kind < 2
        ]

        assert (
            len(empty_default_args) < 2
        ), "Next step must have atmost one param without default value "

        if curr_sig.return_annotation not in (None, inspect._empty):
            assert (
                curr_sig.return_annotation
                == next(iter(next_sig.parameters.values())).annotation
            )
        else:
            assert len(empty_default_args) == 0

        def run(_, var: Any):
            tmp = self(var)
            res = step(tmp)
            return res

        parameters = [inspect.Parameter("__self__", kind=0)] + list(
            curr_sig.parameters.values()
        )

        setattr(
            run,
            "__signature__",
            inspect.Signature(
                parameters=parameters, return_annotation=next_sig.return_annotation
            ),
        )

        _dict = deepcopy(self.__dict__)
        _dict.update(deepcopy(step.__dict__))
        _dict["run"] = run

        plugin = type("Plugin", (BasePlugin,), _dict)()
        return plugin


def asplugin(func: Callable):
    def run(_, *args, **kwargs):
        return func(*args, **kwargs)

    sig = inspect.signature(func)
    parameters = [Parameter("__self__", kind=0)] + list(sig.parameters.values())
    setattr(
        run,
        "__signature__",
        Signature(parameters=parameters, return_annotation=sig.return_annotation),
    )

    return type("Plugin", (BasePlugin,), {"run": run})()
