"""Test fallback gate: try/except in tests is detected; pytest.raises passes."""
from __future__ import annotations

import importlib
import types

import pytest


def _load() -> types.ModuleType:
    # governance/ is on sys.path via governance/tests/conftest.py.
    return importlib.import_module('check_test_fallbacks')


def test_find_try_statements_flags_try() -> None:
    mod = _load()
    src = 'def test_x() -> None:\n    try:\n        do()\n    except Exception:\n        pass\n'
    assert mod.find_try_statements(src) == [2]


def test_find_try_statements_passes_pytest_raises() -> None:
    mod = _load()
    src = (
        'import pytest\n'
        'def test_x() -> None:\n'
        '    with pytest.raises(ValueError):\n'
        '        do()\n'
    )
    assert mod.find_try_statements(src) == []


def test_pure_finally_restores_state_without_catching_assertions() -> None:
    source = ("state = {'restored': False}\n"
              "try:\n    assert False, 'original failure'\n"
              "finally:\n    state['restored'] = True\n")
    assert _load().find_try_statements(source) == []
    namespace = {}
    with pytest.raises(AssertionError, match='original failure'):
        exec(compile(source, '<cleanup-fixture>', 'exec'), namespace)
    assert namespace['state']['restored'] is True


def test_handlers_are_rejected_even_when_finally_also_restores_state() -> None:
    source = ('try:\n    assert False\n'
              'except AssertionError:\n    pass\nfinally:\n    cleanup()\n')
    assert _load().find_try_statements(source) == [1]
    grouped = ('try:\n    assert False\nexcept* AssertionError:\n    pass\n')
    assert _load().find_try_statements(grouped) == [1]
