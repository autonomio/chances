"""Dependency auditing cannot confuse tool failure or missing evidence with safety."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from _dependency_audit import audit


@pytest.fixture
def runtime_lock(tmp_path: Path) -> Path:
    path = tmp_path / 'runtime.txt'
    path.write_text('numpy==2.0 --hash=sha256:' + 'a' * 64 + '\n')
    return path


def _run_result(monkeypatch, payload, code=0, stderr='') -> list[list[str]]:
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, code, json.dumps(payload), stderr)

    monkeypatch.setattr('_dependency_audit.subprocess.run', run)
    return calls


def test_verified_audit_never_resolves_or_executes_local_projects(monkeypatch, runtime_lock: Path) -> None:
    payload = {'dependencies': [{'name': 'numpy', 'version': '2.0', 'vulns': []}]}
    calls = _run_result(monkeypatch, payload)
    assert audit(['numpy>=2,<3'], runtime_lock) == payload['dependencies']
    assert {'--no-deps', '--disable-pip', '--require-hashes', '--strict'} <= set(calls[0])
    assert str(runtime_lock) in calls[0]


@pytest.mark.parametrize('payload', [
    [], {}, {'dependencies': []}, {'dependencies': [None]},
    {'dependencies': [{'name': 'numpy', 'version': '3.0', 'vulns': []}]},
    {'dependencies': [{'name': 'numpy', 'version': '2.0', 'vulns': None}]},
    {'dependencies': [{'name': 'numpy', 'version': '2.0', 'vulns': [{}]}]},
    {'dependencies': [{'name': 'numpy', 'version': '2.0', 'vulns': [{'id': 'A', 'fix_versions': '2'}]}]},
])
def test_incomplete_or_malformed_evidence_blocks(monkeypatch, runtime_lock: Path, payload) -> None:
    _run_result(monkeypatch, payload)
    with pytest.raises(SystemExit):
        audit(['numpy>=2,<3'], runtime_lock)


def test_operational_failure_preserves_the_actual_diagnostic(monkeypatch, runtime_lock: Path, capsys) -> None:
    monkeypatch.setattr('_dependency_audit.subprocess.run', lambda command, **kwargs:
                        subprocess.CompletedProcess(command, 1, '', 'resolver cannot open local file'))
    with pytest.raises(SystemExit):
        audit(['numpy>=2,<3'], runtime_lock)
    assert 'resolver cannot open local file' in capsys.readouterr().err


def test_incompatible_lock_fails_before_subprocess(monkeypatch, runtime_lock: Path) -> None:
    calls = _run_result(monkeypatch, {'dependencies': []})
    with pytest.raises(SystemExit):
        audit(['numpy>=3,<4'], runtime_lock)
    assert not calls


def test_exit_one_needs_real_vulnerability_evidence(monkeypatch, runtime_lock: Path) -> None:
    _run_result(monkeypatch, {'dependencies': [{'name': 'numpy', 'version': '2.0', 'vulns': []}]}, code=1)
    with pytest.raises(SystemExit):
        audit(['numpy>=2,<3'], runtime_lock)
