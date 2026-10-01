"""Typing controls must be recognized, strict and bound to the complete package."""
from __future__ import annotations

import copy
import importlib
from pathlib import Path

import pytest
from _common import loads_toml

ROOT = Path(__file__).resolve().parents[2]
GATE = importlib.import_module('typing_gate')


def _project():
    return loads_toml((ROOT / 'pyproject.toml').read_text())


def test_recognized_policy_does_not_demand_a_ignored_control() -> None:
    project = _project()
    assert 'reportExplicitAny' not in project['tool']['pyright']
    assert 'reportExplicitAny' not in GATE.REQUIRED_PYRIGHT
    assert GATE.gate_pyright_config(project) == []
    project['tool']['pyright']['reportExplicitAny'] = 'error'
    findings = GATE.gate_pyright_config(project)
    assert any('unrecognized' in finding for finding in findings)


@pytest.mark.parametrize('key', ['typeCheckingMode', 'reportMissingImports',
                                'reportUnknownVariableType', 'reportMissingParameterType'])
def test_recognized_typing_controls_cannot_be_weakened(key) -> None:
    project = _project()
    project['tool']['pyright'][key] = 'basic' if key == 'typeCheckingMode' else 'warning'
    assert any(key in finding for finding in GATE.gate_pyright_config(project))


@pytest.mark.parametrize('include', [[], ['chances/_errors.py'], ['missing_package']])
def test_package_analysis_surface_cannot_be_empty_partial_or_missing(include) -> None:
    project = copy.deepcopy(_project())
    project['tool']['pyright']['include'] = include
    assert any('pyright.include' in finding for finding in GATE.gate_pyright_config(project))


def test_typing_workflow_uses_the_interpreter_with_installed_dependencies() -> None:
    workflow = (ROOT / '.github/workflows/pr_checks_typing.yml').read_text()
    assert 'pyright --pythonpath "$(command -v python)" --outputjson' in workflow
    assert '--require-hashes -r requirements/ci/runtime-env.txt' in workflow
