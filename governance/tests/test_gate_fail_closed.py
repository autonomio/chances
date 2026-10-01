"""Governance evidence rejects nonfinite measurements and unreadable protected bases."""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
protected = importlib.import_module('_protected_budget')
budget_gate = importlib.import_module('check_budget_ratchet')
coverage_gate = importlib.import_module('check_coverage_ratchet')
runtime_gate = importlib.import_module('check_test_runtime')
_READERS = [budget_gate._base_budget_from_ref, coverage_gate._base_floor_from_ref,
            lambda ref: runtime_gate.base_ceiling(ref, None)]


def _runtime(tmp_path: Path, *, ceiling: object = 60, base: object = 60,
             total: object = 1, rows: object = None) -> subprocess.CompletedProcess[str]:
    (tmp_path / 'governance').mkdir()
    (tmp_path / '.github').mkdir()
    for name in ('_common.py', '_protected_budget.py', 'check_test_runtime.py'):
        (tmp_path / 'governance' / name).write_bytes((REPO_ROOT / 'governance' / name).read_bytes())
    (tmp_path / '.github/budgets.json').write_text(json.dumps({'runtime': {'max_total_seconds': ceiling}}))
    (tmp_path / 'base.json').write_text(json.dumps({'runtime': {'max_total_seconds': base}}))
    (tmp_path / 'profile.json').write_text(json.dumps({'total_seconds': total, 'tests': [] if rows is None else rows}))
    (tmp_path / 'body.txt').write_text('[runtime-raise: this marker cannot permit malformed evidence]')
    return subprocess.run([sys.executable, str(tmp_path / 'governance/check_test_runtime.py'),
                           '--profile', str(tmp_path / 'profile.json'), '--enforce',
                           '--base-file', str(tmp_path / 'base.json'),
                           '--pr-body-file', str(tmp_path / 'body.txt')], cwd=tmp_path,
                          capture_output=True, text=True, check=False)


@pytest.mark.parametrize('field', ['ceiling', 'base', 'total'])
@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf'), -1, True, None, '1', 10**400])
def test_invalid_runtime_numbers_fail_setup(tmp_path: Path, field: str, value: object) -> None:
    result = _runtime(tmp_path, **{field: value})
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'must be finite' in result.stderr
    assert '-- PASS' not in result.stdout


@pytest.mark.parametrize('field', ['ceiling', 'base'])
def test_zero_ceiling_is_invalid(tmp_path: Path, field: str) -> None:
    result = _runtime(tmp_path, **{field: 0})
    assert result.returncode == 2


@pytest.mark.parametrize('duration', [float('nan'), float('inf'), -float('inf'), -1, True, None, '1', 10**400])
def test_invalid_individual_durations_fail_setup(tmp_path: Path, duration: object) -> None:
    result = _runtime(tmp_path, rows=[{'name': 'test_case', 'duration': duration}])
    assert result.returncode == 2
    assert 'profile test duration must be finite' in result.stderr


@pytest.mark.parametrize('row', [None, 1, {}, {'name': '', 'duration': 1},
                                 {'name': False, 'duration': 1}, {'name': '  ', 'duration': 1}])
def test_malformed_profile_rows_are_visible(tmp_path: Path, row: object) -> None:
    result = _runtime(tmp_path, rows=[row])
    assert result.returncode == 2
    assert 'profile test rows must have nonempty string names' in result.stderr


def test_runtime_zero_measurements_are_valid(tmp_path: Path) -> None:
    result = _runtime(tmp_path, total=0, rows=[{'name': 'test_case', 'duration': 0}])
    assert result.returncode == 0, result.stderr


def test_runtime_overrun_remains_blocking(tmp_path: Path) -> None:
    result = _runtime(tmp_path, total=61)
    assert result.returncode == 1
    assert 'suite took 61.00s' in result.stderr


def _repository(tmp_path: Path, content: str | None = None) -> str:
    subprocess.run(['git', 'init', '--quiet'], cwd=tmp_path, check=True)
    (tmp_path / 'README.md').write_text('Declared throwaway governance fixture.\n')
    if content is not None:
        (tmp_path / '.github').mkdir(exist_ok=True)
        (tmp_path / '.github/budgets.json').write_text(content)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '--quiet', '-m', 'test: establish protected fixture'], cwd=tmp_path, check=True)
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.mark.parametrize('reader', _READERS)
def test_unreachable_protected_base_fails_setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reader: object) -> None:
    _repository(tmp_path)
    monkeypatch.setattr(protected, 'REPO_ROOT', tmp_path)
    with pytest.raises(SystemExit) as failure:
        reader('never-fetched')
    assert failure.value.code == 2


@pytest.mark.parametrize('reader,expected', list(zip(_READERS, [{}, {}, None], strict=True)))
def test_only_reachable_base_without_budget_is_initial_adoption(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reader: object, expected: object) -> None:
    commit = _repository(tmp_path)
    monkeypatch.setattr(protected, 'REPO_ROOT', tmp_path)
    assert reader(commit) == expected


@pytest.mark.parametrize('reader', _READERS)
def test_missing_git_fails_setup(monkeypatch: pytest.MonkeyPatch, reader: object) -> None:
    def missing(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError('declared missing Git fixture')
    monkeypatch.setattr(protected.subprocess, 'run', missing)
    with pytest.raises(SystemExit) as failure:
        reader('HEAD')
    assert failure.value.code == 2


@pytest.mark.parametrize('operation', ['ls-tree', 'show'])
def test_failed_tree_or_blob_reads_are_not_absent_budgets(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str) -> None:
    commit = _repository(tmp_path, '{}')
    monkeypatch.setattr(protected, 'REPO_ROOT', tmp_path)
    original = subprocess.run
    def interrupted(arguments: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if arguments[1] == operation:
            return subprocess.CompletedProcess(arguments, 1, '', 'declared Git read failure')
        return original(arguments, **kwargs)
    monkeypatch.setattr(protected.subprocess, 'run', interrupted)
    with pytest.raises(SystemExit) as failure:
        protected.protected_budget_text(commit, 'TEST')
    assert failure.value.code == 2


def test_protected_reader_ignores_modified_checkout_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    content = json.dumps({'modules': {'pkg/mod.py': 100}, 'coverage': {'line': 92, 'branch': 87},
                          'runtime': {'max_total_seconds': 60}})
    commit = _repository(tmp_path, content)
    (tmp_path / '.github/budgets.json').write_text('{}')
    monkeypatch.setattr(protected, 'REPO_ROOT', tmp_path)
    assert budget_gate._base_budget_from_ref(commit) == {'pkg/mod.py': 100}
    assert coverage_gate._base_floor_from_ref(commit) == {'line': 92, 'branch': 87}
    assert runtime_gate.base_ceiling(commit, None) == 60


@pytest.mark.parametrize('kind', ['empty', 'symlink', 'directory'])
def test_contradicted_budget_presence_fails_setup(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    _repository(tmp_path)
    (tmp_path / '.github').mkdir()
    path = tmp_path / '.github/budgets.json'
    if kind == 'empty':
        path.write_text('  ')
    elif kind == 'symlink':
        path.symlink_to('../README.md')
    else:
        path.mkdir()
        (path / 'inside').write_text('{}')
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '--quiet', '-m', 'test: contradict budget fixture'], cwd=tmp_path, check=True)
    monkeypatch.setattr(protected, 'REPO_ROOT', tmp_path)
    with pytest.raises(SystemExit) as failure:
        protected.protected_budget_text('HEAD', 'TEST')
    assert failure.value.code == 2


@pytest.mark.parametrize('reader', _READERS)
@pytest.mark.parametrize('content', ['[]', 'null', '{'])
def test_malformed_protected_budget_is_a_setup_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reader: object, content: str) -> None:
    commit = _repository(tmp_path, content)
    monkeypatch.setattr(protected, 'REPO_ROOT', tmp_path)
    with pytest.raises(SystemExit) as failure:
        reader(commit)
    assert failure.value.code == 2


@pytest.mark.parametrize('rows', [{}, True, 'declared malformed profile'])
def test_profile_test_collection_is_a_list(tmp_path: Path, rows: object) -> None:
    result = _runtime(tmp_path, rows=rows)
    assert result.returncode == 2
    assert 'profile .tests must be a list' in result.stderr
