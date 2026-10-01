"""Manual bootstrap refuses existing products before any write or privileged use."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / '.github/workflows/bootstrap_repository.yml'
BOOTSTRAP_SCRIPT = REPO_ROOT / 'governance/bootstrap_repository.py'


def _guard() -> str:
    payload = yaml.safe_load(WORKFLOW.read_text())
    triggers = payload.get('on', payload.get(True))
    assert set(triggers) == {'workflow_dispatch'}
    steps = payload['jobs']['bootstrap']['steps']
    position = next(i for i, step in enumerate(steps) if step['name'].startswith('Guard fresh'))
    assert position < next(i for i, step in enumerate(steps) if 'Rewrite' in step['name'])
    run = steps[position]['run']
    return run.split("python - <<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]


def _run_guard(repo: Path, repository: str, confirmed: str, ref: str):
    return subprocess.run(
        [sys.executable, '-c', _guard()], cwd=repo, capture_output=True, text=True, check=False,
        env={**os.environ, 'REPOSITORY': repository, 'CONFIRMED_REPOSITORY': confirmed,
             'DISPATCH_REF': ref},
    )


def test_guard_accepts_only_a_confirmed_fresh_seed(seed_repository: Path) -> None:
    result = _run_guard(seed_repository, 'Autonomio/fresh-seed', 'Autonomio/fresh-seed',
                        'refs/heads/master')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(('repository', 'confirmed', 'ref'), [
    ('autonomio/chances', 'autonomio/chances', 'refs/heads/master'),
    ('Autonomio/fresh-seed', 'Autonomio/other-seed', 'refs/heads/master'),
    ('Autonomio/fresh-seed', 'Autonomio/fresh-seed', 'refs/heads/feature'),
])
def test_guard_rejects_existing_chances_wrong_confirmation_and_ref(
    seed_repository: Path, repository: str, confirmed: str, ref: str,
) -> None:
    result = _run_guard(seed_repository, repository, confirmed, ref)
    assert result.returncode != 0 and result.stderr


def test_guard_rejects_scientific_code_even_if_metadata_is_forged(seed_repository: Path) -> None:
    (seed_repository / 'chances').mkdir()
    result = _run_guard(seed_repository, 'Autonomio/fresh-seed', 'Autonomio/fresh-seed',
                        'refs/heads/master')
    assert result.returncode != 0


def test_rename_engine_leaves_workflow_files_alone() -> None:
    tree = ast.parse(BOOTSTRAP_SCRIPT.read_text())
    branches = [node for node in ast.walk(tree) if isinstance(node, ast.If)
                and _tests_for_workflows_prefix(node.test)
                and any(isinstance(statement, ast.Continue) for statement in node.body)]
    assert branches, 'specialization must not rewrite workflow authorization guards'


def _tests_for_workflows_prefix(test: ast.expr) -> bool:
    return any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
               and node.func.attr == 'startswith'
               and any(isinstance(arg, ast.Constant) and arg.value == '.github/workflows/'
                       for arg in node.args)
               for node in ast.walk(test))
