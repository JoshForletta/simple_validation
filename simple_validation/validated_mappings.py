from __future__ import annotations

from abc import ABCMeta
from collections import defaultdict
from collections.abc import MutableMapping
from typing import Any, Callable, Generic, Iterator, MutableMapping as MutableMappingT, Type, TypeAlias, TypeVar

from ._base import FailedValidation, _format_failed_validations



_KT = TypeVar('_KT')
_VT = TypeVar('_VT')
_IKT = TypeVar('_IKT')
_IVT = TypeVar('_IVT')
Self = TypeVar('Self')

_kvp_validatorsT: TypeAlias = dict[
    tuple[Type[_IKT], Type[_IVT]], 
    set[Callable[[Self, _IKT, _IVT], tuple[_KT, _VT]]]
]

class ExceptedInputs(Generic[_IKT, _IVT]):
    pass


class ValidatedMappingMeta(type):
    def __new__(
        mcls: Self, 
        name: str, 
        bases: tuple[type], 
        namespace: dict[str, Any], 
        **kwargs: Any
    ) -> Self:
        kv_validators = namespace['_kv_validators'] = {}
        k_validators = namespace['_k_validators'] = {}
        v_validators = namespace['_v_validators'] = {}

        for k, o in namespace.items():
            if hasattr(o, '__validates_kvts__'): 
                kv_validators.setdefault(getattr(o, '__validates_kvts__'), set()).add(o)
            if hasattr(o, '__validates_kts__'): 
                for t in getattr(o, '__validates_kts__'):
                    k_validators.setdefault(t, set()).add(o)
            if hasattr(o, '__validates_vts__'): 
                for t in getattr(o, '__validates_vts__'):
                    v_validators.setdefault(t, set()).add(o)

        return super().__new__(mcls, name, bases, namespace, **kwargs)


class ValidatedMappingABCMeta(ValidatedMappingMeta, ABCMeta): pass


class ValidatedMapping(
    ExceptedInputs[_IKT, _IVT], 
    MutableMapping[_KT, _VT], 
    metaclass=ValidatedMappingABCMeta
):
    _kv_validators: defaultdict[
        tuple[Type[_IKT], Type[_IVT]], 
        set[Callable[[ValidatedMapping, _IKT, _IVT], tuple[_KT, _VT]]]
    ]
    _k_validators: defaultdict[
        Type[_IKT], 
        set[Callable[[ValidatedMapping, _IKT, _IVT], tuple[_KT, _VT]]]
    ]
    _v_validators: defaultdict[
        Type[_IVT], 
        set[Callable[[ValidatedMapping, _IKT, _IVT], tuple[_KT, _VT]]]
    ]

    _validate_keys: bool = True
    _validate_values: bool = True

    def __init__(self: Self, *args: dict[_KT, _VT], **kwargs: _VT) -> None:
        self._store = {}
        self.update(dict(*args, **kwargs))

    def __getitem__(self, k: _KT, /) -> _VT:
        return self._store[k]

    def __setitem__(self, k: _IKT, v: _IVT, /) -> None:
        k, v = self.validate(k, v)
        self._store[k] = v

    def __delitem__(self, k: _KT) -> None:
        del self._store[k]

    def __iter__(self) -> Iterator[_KT]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def _validate_kv(self, k: _IKT, v: _IVT) -> tuple[_KT, _VT]:
        failed_validations = []
        kvts = type(k), type(v)

        for validator in self._kv_validators[kvts]:
            try: return validator(self, k, v)
            except FailedValidation as e: 
                failed_validations.append((
                    validator.__name__, f"key={k!r}, value={v!r}", e
                ))

        raise FailedValidation(_format_failed_validations(failed_validations))
  

    def validate(self, k: _IKT, v: _IVT) -> tuple[_KT, _VT]:
        failed_validations = []
        kvts = (kt, vt) = type(k), type(v)

        if kvts in self._kv_validators: return self._validate_kv(k, v)

        if self._validate_keys == False: vk = k
        elif not self._k_validators.get(kt, None): 
            failed_validations.append((
                f"{type(self).__name__}.validate", 
                f"key={k!r}",
                FailedValidation(f"No key validators specified for type `{kt}`")
            ))
        else:
            for validator in self._k_validators[kt]:
                try: vk = validator(self, k)
                except FailedValidation as e: 
                    failed_validations.append((validator.__name__, f"key={k!r}", e))

        if self._validate_values == False: vv = v
        elif not self._v_validators.get(vt, None):
            failed_validations.append((
                f"{type(self).__name__}.validate",
                f"value={v}",
                FailedValidation(f"No value validators specified for type `{vt}`")
            ))
        else:
            for validator in self._v_validators[vt]:
                try: vv = validator(self, v)
                except FailedValidation as e: 
                    failed_validations.append((validator.__name__, f"value={v}", e))

        try: return vk, vv
        except UnboundLocalError: 
            raise FailedValidation(_format_failed_validations(failed_validations))
        

def kv_validator(
    key_type: Type[_IKT], value_type: Type[_IVT]
) -> Callable[
    [Callable[[_IKT, _IVT], tuple[_KT, _VT]]], 
    Callable[[_IKT, _IVT], tuple[_KT, _VT]]
]:
    def decorator(
        func: Callable[[_IKT, _IVT], tuple[_KT, _VT]]
    ) -> Callable[[_IKT, _IVT], tuple[_KT, _VT]]:
        func.__validates_kvts__ = (key_type, value_type)
        return func
    return decorator


def k_validator(*key_types: _IKT) -> Callable[[Callable[[_IKT], _KT]], Callable[[_IKT], _KT]]:
    def decorator(func: Callable[[_IKT], _KT]) -> Callable[[_IKT], _KT]:
        func.__validates_kts__ = key_types
        return func
    return decorator

def v_validator(*value_types: _IVT) -> Callable[[Callable[[_IVT], _VT]], Callable[[_IVT], _VT]]:
    def decorator(func: Callable[[_IVT], _KT]) -> Callable[[_IVT], _VT]:
        func.__validates_vts__ = value_types
        return func
    return decorator
