"""Snapshot copy parity and isolation: local object graphs only."""
from collections import defaultdict, namedtuple
from copy import deepcopy
from datetime import datetime, date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from markupsafe import Markup

from engines.snapshot_copy_engine import clone_snapshot


@pytest.mark.parametrize('value', [None, False, True, 0, -5, 10**80, 0.0, -0.0,
    'Ñ · Madrid', b'bytes', 1+2j, '', [] ,{}, (1, 2), range(5),
    datetime(2026, 10, 25, 2, 30, tzinfo=ZoneInfo('Europe/Madrid'), fold=1),
    date(2026, 9, 21), timedelta(seconds=3), Decimal('0.00'), {1, 2},
    frozenset({1, 2}), bytearray(b'abc'), Markup('<b>safe</b>'),
    defaultdict(list, values=[1, {'x': 2}]), SimpleNamespace(items=[0, 2]),
    namedtuple('Result', 'home away')(0, 1)])
def test_values_and_exact_types_match_deepcopy(value):
    result = clone_snapshot(value)
    assert result == deepcopy(value)
    assert type(result) is type(value)


def test_nested_aliases_preserved_inside_not_between_callers():
    match = {'id': 'qa-1', 'score': [0, 1], 'coverage': {'stats': [0, None]}}
    original = {'today': [match], 'all': [match], 'nested': {'match': match}}
    first, second = clone_snapshot(original), clone_snapshot(original)
    assert first == second == deepcopy(original)
    assert first['today'][0] is first['all'][0] is first['nested']['match']
    first['today'][0]['score'][0] = 7
    first['all'][0]['coverage']['stats'].append(5)
    assert second['today'][0]['score'] == original['today'][0]['score'] == [0, 1]
    assert second['today'][0]['coverage']['stats'] == [0, None]


def test_recursive_dict_list_graph():
    original = {'items': []}
    original['self'] = original
    original['items'].extend([original, original['items']])
    result = clone_snapshot(original)
    assert result is not original and result['self'] is result
    assert result['items'][0] is result and result['items'][1] is result['items']
    assert result['items'] is not original['items']


def test_fallback_tuple_cycle_uses_the_same_memo():
    original = {'list': []}
    original['tuple'] = (original, original['list'])
    original['list'].append(original['tuple'])
    result = clone_snapshot(original)
    assert result['tuple'][0] is result
    assert result['tuple'][1] is result['list']
    assert result['list'][0] is result['tuple']


class CopyHook:
    def __init__(self, child):
        self.child = child
    def __deepcopy__(self, memo):
        result = type(self).__new__(type(self))
        memo[id(self)] = result
        result.child = deepcopy(self.child, memo)
        result.hook_called = True
        return result


class DictSubclass(dict):
    pass


class ListSubclass(list):
    pass


@pytest.mark.parametrize('wrapper', [CopyHook, DictSubclass, ListSubclass])
def test_custom_types_keep_deepcopy_protocol(wrapper):
    source = {'items': [0]}
    if wrapper is CopyHook:
        source['custom'] = CopyHook(source)
    elif wrapper is DictSubclass:
        source['custom'] = wrapper(ref=source)
    else:
        source['custom'] = wrapper([source])
    result = clone_snapshot(source)
    custom = result['custom']
    assert type(custom) is wrapper
    if wrapper is CopyHook:
        assert custom.hook_called and custom.child is result
    elif wrapper is DictSubclass:
        assert custom['ref'] is result
    else:
        assert custom[0] is result


def test_mutable_hashable_key_and_value_retain_alias():
    key = CopyHook([1])
    result = clone_snapshot({key: key})
    cloned_key = next(iter(result))
    assert cloned_key is result[cloned_key] and cloned_key is not key
    assert cloned_key.child == [1] and cloned_key.child is not key.child


def test_copy_failure_is_not_hidden_or_shared():
    class Uncopyable:
        def __deepcopy__(self, memo):
            raise ValueError('test copy failure')
    with pytest.raises(ValueError, match='test copy failure'):
        clone_snapshot({'unavailable': Uncopyable()})
