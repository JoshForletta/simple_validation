from __future__ import annotations
from collections import defaultdict
import functools
from io import StringIO
from typing import Any, Callable, ParamSpec, Type, TypeAlias, TypeVar

from ._base import FailedValidation, _format_failed_validations


Self = TypeVar('Self')
_T = TypeVar('_T')
_OT = TypeVar('_OT')
_P = ParamSpec('_P')
_R = TypeVar('_R')


class ValidatedAttr():

    def __init__(self) -> None:
        self._validators: defaultdict[type, set[Callable[[_T, Any], Any]]] = defaultdict(set)
        self._prevalidation_setters = defaultdict(lambda: lambda i, v: v)
        self._getter = lambda i: getattr(i, self.private_name)
        self._setter = lambda i, v: setattr(i, self.private_name, v)

    def __set_name__(self, cls: Type[_T], name: str) -> None:
        self.name = name
        self.private_name = f'_{name}' if name[0] != '_' else f'{name}_'

    def __get__(self, instance: _T, objtype=None) -> _R:
        return self._getter(instance)

    def __set__(self, instance: _T, value: _R) -> None:
        self._setter(instance, self._validate(instance, self._prevalidation_setters[type(value)](instance, value)))

    def getter(self, func: Callable[[_T], Any]) -> Callable[[_T], Any]:
        self._getter = func
        return func

    def setter(self, func: Callable[[_T, _OT], None]) -> Callable[[_T, _OT], None]:
        self._setter = func
        return func

    def _validate(self, instance: _T, value: _OT) -> Any:
        failed_validations = []
        validators = self._validators.get(type(value), self._validators[None])

        for validator in validators: 
            try: return validator(instance, value)
            except FailedValidation as e: 
                failed_validations.append((validator.__name__, value, e))

        raise FailedValidation(_format_failed_validations(failed_validations))

    def validator(
        self, *types
    ) -> Callable[[Callable[[_T, _OT], _R]], Callable[[_T, _OT], _R]]:
        def decorator(func: Callable[[_T, _OT], _R]) -> Callable[[_T, _OT], _R]:
            @functools.wraps(func)
            def wrapper(instance: _T, o: _OT) -> _T:
                return func(instance, o)
            
            for t in types: self._validators[t].add(wrapper)

            return wrapper
        return decorator

    def classvalidator(
        self, *types
    ) -> Callable[[Callable[[Type[_T]], _OT], _R], Callable[[_T, _OT], _R]]:
        def decorator(func: Callable[[Type[_T], _OT], _R]) -> Callable[[_T, _OT], _R]:
            @functools.wraps(func)
            def wrapper(instance: _T, o: _OT) -> _T:
                return func(type(instance), o)
            
            for t in types: self._validators[t].add(wrapper)

            return wrapper
        return decorator

    def staticvalidator(
        self, *types
    ) -> Callable[[Callable[[_T, _OT], _R]], Callable[[_T, _OT], _R]]:
        def decorator(func: Callable[[_OT], _R]) -> Callable[[_T, _OT], _R]:
            @functools.wraps(func)
            def wrapper(instance: _T, o: _OT) -> _R:
                return func(o)
            
            for t in types: self._validators[t].add(wrapper)

            return wrapper
        return decorator
