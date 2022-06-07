from __future__ import annotations
from collections import defaultdict
import functools
from typing import Any, Callable, ParamSpec, Type, TypeVar


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
    __validators__: defaultdict[_KT, set[str]]

    def __new__(cls: Type[Self], *arg, **kwargs) -> Self:
        o: Self = super().__new__(cls)
        o.__validators__ = defaultdict(set)

        for attr_name, attr in o.__class__.__dict__.items():
            if not hasattr(attr, '__validate_types__'): continue
            
            for t in attr.__validate_types__:
                o.__validators__[t].add(attr_name)

        return o

    @property
    def _failed_validation_msgs(self):
        pass
    
    def validate(self, o: _T) -> _R:
        fail_msgs = self.__dict__.setdefault('_validation_fail_msgs', set())
        validators = self.__validators__.get(type(o), self.__validators__[None])
        # print('VALIDATE', fail_msgs, validators)

        if not validators: raise FailedValidation(
            f"No validators specified for type `{type(o)}`"
        )

        for v_name in validators:
            try: 
                rv = getattr(self, v_name)(o)
            except FailedValidation as e: 
                fail_msgs.add((v_name, e.args))
            else:
                del fail_msgs
                return rv
            
        fail_msgs_copy = fail_msgs.copy()
        del fail_msgs
        raise FailedValidation(
            "\n\t{}".format(
                '\n\t'.join(
                    (
                        "{}:\n\t\t{}".format(n, '\n\t\t'.join(ms)) 
                        if len(ms) > 1 else f"{n}: {ms[0]}"
                        for n, ms in fail_msgs_copy
                    )
                )
            )
        )





def validator(*types: Type[_T]) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    def decorator(func: Callable[_P, _R]) -> Callable[_P, _R]:
        func.__validate_types__ = types if types else (None,)
        return func
    return decorator
