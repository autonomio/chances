"""Bootstrap is tested in bounded seeds; Chances specialization never rewrites."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def bootstrapped(seed_repository: Path) -> Path:
    """Run the actual rename CLI over a fresh, explicit seed fixture."""
    result = subprocess.run(
        [sys.executable, 'governance/bootstrap_repository.py', '--files-only',
         '--repo-name', 'my-new-app', '--owner', 'Autonomio'],
        cwd=seed_repository, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return seed_repository


def test_bootstrapped_repository_passes_scanning_gates(bootstrapped: Path) -> None:
    """A specialized seed has valid budgets, scan paths and module contracts."""
    for name in ('check_module_budgets', 'check_module_docstrings',
                 'check_file_size_balance', 'check_test_code_ratio'):
        result = subprocess.run(
            [sys.executable, f'governance/{name}.py'], cwd=bootstrapped,
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', 'tests/package', '-q'],
        cwd=bootstrapped, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_regenerated_budgets_fit_the_modules_they_budget(bootstrapped: Path) -> None:
    budgets = json.loads((bootstrapped / '.github/budgets.json').read_text())['modules']
    assert budgets and 'my_new_app/__init__.py' in budgets
    for relative, budget in budgets.items():
        path = bootstrapped / relative
        assert path.is_file(), relative
        significant = sum(bool(line.strip()) and not line.strip().startswith('#')
                          for line in path.read_text().splitlines())
        assert significant <= budget, relative


def test_no_placeholder_token_survives_bootstrap(bootstrapped: Path) -> None:
    tokens = ['{' + name + '}' for name in
              ('REPOSITORY_NAME', 'DISPLAY_NAME', 'REPOSITORY_OWNER', 'ONE_SENTENCE_DESCRIPTION')]
    for path in bootstrapped.rglob('*'):
        if not path.is_file() or path.suffix not in {'.md', '.json', '.toml', '.cff', '.yml'}:
            continue
        assert not any(token in path.read_text() for token in tokens), path
    assert (bootstrapped / 'my_new_app').is_dir()
    assert not (bootstrapped / ('new' + '_repository_' + 'template')).exists()


def test_existing_chances_file_bootstrap_preserves_every_byte(tmp_path: Path) -> None:
    """An existing project cannot lose identity, scientific code or measured budgets."""
    repo = tmp_path / 'chances'
    shutil.copytree(REPO_ROOT, repo, ignore=shutil.ignore_patterns(
        '.git', '.venv*', 'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache',
        '.hypothesis', '.generated', '.docusaurus', 'build', 'dist', '.coverage', 'coverage.json',
    ))
    before = {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in repo.rglob('*') if p.is_file()}
    result = subprocess.run(
        [sys.executable, 'governance/bootstrap_repository.py', '--files-only',
         '--repo-name', 'unrelated-name', '--owner', 'unrelated-owner'],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'already specialized' in result.stdout
    after = {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in repo.rglob('*') if p.is_file()}
    assert after == before


@pytest.mark.parametrize('mode', [
    ['--files-only', '--codeql', 'unsupported'], ['--github-only'], [],
])
def test_established_product_rejects_privileged_or_gate_removing_modes(tmp_path: Path, mode) -> None:
    repo = tmp_path / 'existing'
    (repo / 'governance').mkdir(parents=True)
    shutil.copy2(REPO_ROOT / 'governance/bootstrap_repository.py', repo / 'governance/bootstrap_repository.py')
    (repo / 'chances').mkdir()
    (repo / 'chances/__init__.py').write_text('SCIENCE = "preserved"\n')
    (repo / 'pyproject.toml').write_text('[project]\nname = "chances"\n')
    (repo / 'governance.yml').write_text('gates:\n  codeql:\n    required: true\n')
    before = {p.relative_to(repo).as_posix(): p.read_bytes() for p in repo.rglob('*') if p.is_file()}
    result = subprocess.run(
        [sys.executable, 'governance/bootstrap_repository.py', '--repo-name', 'chances',
         '--owner', 'autonomio', *mode], cwd=repo, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert 'existing product' in result.stderr
    assert {p.relative_to(repo).as_posix(): p.read_bytes() for p in repo.rglob('*') if p.is_file()} == before


def test_adding_a_seed_directory_cannot_rewrite_chances(seed_repository: Path) -> None:
    (seed_repository / 'chances').mkdir()
    result = subprocess.run(
        [sys.executable, 'governance/bootstrap_repository.py', '--files-only',
         '--repo-name', 'my-new-app', '--owner', 'Autonomio'],
        cwd=seed_repository, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0 and 'existing product' in result.stderr
    assert not (seed_repository / 'my_new_app').exists()


@pytest.mark.parametrize('mode', [['--files-only'], ['--github-only'], []])
def test_other_product_cannot_forge_seed_identity(seed_repository: Path, mode) -> None:
    project = seed_repository / 'pyproject.toml'
    project.write_text(project.read_text().replace('name = "new-repository-template"', 'name = "other-product"'))
    before = {p.relative_to(seed_repository).as_posix(): p.read_bytes()
              for p in seed_repository.rglob('*') if p.is_file()}
    result = subprocess.run(
        [sys.executable, 'governance/bootstrap_repository.py', '--repo-name', 'replacement',
         '--owner', 'autonomio', *mode], cwd=seed_repository,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0 and 'existing product' in result.stderr
    assert 'GH_TOKEN' not in result.stderr
    assert {p.relative_to(seed_repository).as_posix(): p.read_bytes()
            for p in seed_repository.rglob('*') if p.is_file()} == before
