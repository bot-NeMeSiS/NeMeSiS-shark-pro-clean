"""Isolated copies of in-memory snapshot graphs, without JSON/type conversion.

Fast paths cover only exact built-in dictionaries, lists and immutable scalar
values. All other types retain Python's deepcopy protocol with the same memo.
No global monkeypatch, persistence, serialization, cache or provider access.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

_ATOMIC_TYPES = frozenset({str, int, float, bool, bytes, complex, type(None)})


def clone_snapshot(value: Any) -> Any:
    """Copy a snapshot, retaining internal aliases/cycles, not mutable inputs.

    A separate memo for each call keeps separate callers isolated. Subclasses,
    dates, tuples and objects with custom copy hooks use standard deepcopy.
    Immutable leaves are shared as they are by deepcopy, not mutable containers.
    """
    return _clone(value, {})


def _clone(value: Any, memo: dict[int, Any]) -> Any:
    kind = type(value)
    if kind in _ATOMIC_TYPES:
        return value
    identity = id(value)
    if identity in memo:
        return memo[identity]
    if kind is dict:
        result: dict[Any, Any] = {}
        memo[identity] = result
        for key, item in value.items():
            result[key if type(key) in _ATOMIC_TYPES else _clone(key, memo)] = (
                item if type(item) in _ATOMIC_TYPES else _clone(item, memo)
            )
        return result
    if kind is list:
        copied: list[Any] = []
        memo[identity] = copied
        copied.extend(item if type(item) in _ATOMIC_TYPES else _clone(item, memo) for item in value)
        return copied
    return deepcopy(value, memo)
