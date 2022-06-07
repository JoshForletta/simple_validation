from __future__ import annotations
from collections import defaultdict
import functools
from typing import Any, Callable, ParamSpec, Type, TypeAlias, TypeVar


Self = TypeVar('Self')
_T = TypeVar('_T')
_P = ParamSpec('_P')
_R = TypeVar('_R')

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')



class FailedValidation(Exception):
    pass


class Validated():
    _validation_fail_msgs: list[tuple[str, tuple[str]]]
    __validators__: defaultdict[_KT, set[str]] = defaultdict(set)

    @property
    def _current_validation_frame(self) -> list[tuple[str, list]]:
        try: return self.__dict__['_validation_frame'][-1][1]
        except KeyError: return self.__dict__.setdefault('_validation_frame', [])


    def validate(self, o: _T) -> _R:
        validators = self.__validators__.get(type(o), self.__validators__[None])

        if not validators: raise FailedValidation(
            f"No validators specified for type `{type(o)}`"
        )

        cache = self.__dict__.setdefault('__validation_cache__', {})
        for v_name in validators:
            if (v_name, o) in cache: continue
            try: 
                rv = getattr(self, v_name)(o)
            except FailedValidation as e: pass
            else:
                return rv

        raise FailedValidation(
            "\n\t" + "\n\t".join(
                "{}({}):\n\t\t{}".format(
                    k[0], repr(k[1]), "\n\t\t".join(e.args)
                ) for k, e in cache.items()
            )
        )


class ValidatorDescriptor():
    def __init__(
        self, 
        func: Callable[_P, _T], 
        *, 
        types: tuple[type], 
        cache: bool
    ) -> Callable[_P, _T]:
        self.func = func
        self.types = types
        self.cache = cache

    def __set_name__(self, cls: type, name) -> None:
        self.cls = cls
        if not '__validators__' in cls.__dict__: 
            cls.__validators__ = defaultdict(set)

        for t in self.types:
            cls.__validators__[t].add(name)

    def __get__(self, instance, objtype=None) -> Callable[_P, _T]:
        return functools.partial(self.__call__, instance, instance)

    def __call__(self, instance: Validated, *args) -> None:
        try: return self.func(*args)
        except FailedValidation as e: 
            if self.cache and instance is not None: 
                instance.__dict__.setdefault('__validation_cache__', {})\
                    [(self.func.__name__, args[-1])] = e
            raise e



class ClassValidatorDescriptor(ValidatorDescriptor):
    def __get__(self, instance, objtype=None) -> Callable[_P, _T]:
        return functools.partial(self.__call__, instance, self.cls)


class StaticValidatorDescriptor(ValidatorDescriptor):
    def __get__(self, instance, objtype=None) -> Callable[_P, _T]:
        return functools.partial(self.__call__, instance)
    

def validator(*types, cache: bool = True):
    def decorator(func: Callable) -> Callable:
        return functools.wraps(func)(ValidatorDescriptor(func, types=types, cache=cache))
    return decorator

def classvalidator(*types, cache: bool = True):
    def decorator(func: Callable) -> Callable:
        return functools.wraps(func)(ClassValidatorDescriptor(func, types=types, cache=cache))
    return decorator

def staticvalidator(*types, cache: bool = True):
    def decorator(func: Callable) -> Callable:
        return functools.wraps(func)(StaticValidatorDescriptor(func, types=types, cache=cache))
    return decorator


