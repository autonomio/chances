"""Protected historical versions are literal Git metadata, never imported code."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from _base_version import hatch_literal_version

from governance import version_gate


@pytest.fixture
def historical_repo(tmp_path: Path, monkeypatch):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    monkeypatch.setattr('_base_version.REPO_ROOT', tmp_path)
    return tmp_path


def _commit(repo: Path, source='__version__ = "0.1.9"\n', path='pkg/__init__.py', *, project=None):
    metadata = project if project is not None else (
        '[project]\nname="chances"\ndynamic=["version"]\n'
        f'[tool.hatch.version]\npath="{path}"\n'
    )
    (repo / 'pyproject.toml').write_text(metadata)
    if path == 'pkg/__init__.py':
        target = repo / path
        target.parent.mkdir(exist_ok=True)
        target.write_text(source)
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'feat: declare fixture metadata'], cwd=repo, check=True)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=repo, check=True,
                            capture_output=True, text=True).stdout.strip()
    return metadata, commit


def test_historical_source_is_not_executed_and_checkout_edits_cannot_change_it(historical_repo):
    repo = historical_repo
    marker = repo / 'executed'
    metadata, commit = _commit(repo, f'raise RuntimeError("do not import")\n__version__ = "0.1.9"\n'
                               f'open({str(marker)!r}, "w").write("executed")\n')
    (repo / 'pkg/__init__.py').write_text('__version__ = "99.0.0"\n')
    assert hatch_literal_version(metadata, commit) == '0.1.9'
    assert not marker.exists()


@pytest.mark.parametrize('source', [
    'VERSION = "0.1.9"\n', '__version__ = str("0.1.9")\n', '__version__ = 19\n',
    '__version__ = "0.1.9"\n__version__ = "0.2.0"\n',
    'if True:\n    __version__ = "0.1.9"\n',
    '__version__ = "0.1.9"\ndel __version__\n', '__version__ = "0.1.9"\n__version__ += "x"\n',
    '__version__ = "0.1.9"\ndef f():\n    __version__ = "0.2.0"\n',
    '__version__ = "01.1.9"\n', '__version__ = "0.1.9-alpha"\n',
    '__version__ = "nonsense"\n', '__version__ = (\n',
])
def test_missing_nonliteral_conflicting_and_malformed_versions_fail(historical_repo, source):
    metadata, commit = _commit(historical_repo, source)
    with pytest.raises(SystemExit) as error:
        hatch_literal_version(metadata, commit)
    assert error.value.code == 2


@pytest.mark.parametrize('path', ['../outside.py', '/absolute.py', './pkg/__init__.py',
                                  'pkg/readme.txt', 'missing.py', 'pkg:x.py'])
def test_unsafe_or_missing_declared_paths_fail(historical_repo, path):
    metadata, commit = _commit(historical_repo, path=path)
    with pytest.raises(SystemExit):
        hatch_literal_version(metadata, commit)


def test_pyproject_must_match_the_protected_commit(historical_repo):
    metadata, commit = _commit(historical_repo)
    with pytest.raises(SystemExit):
        hatch_literal_version(metadata + '\n', commit)


def test_missing_ref_and_dynamic_head_still_fail(historical_repo):
    metadata, commit = _commit(historical_repo)
    with pytest.raises(SystemExit):
        hatch_literal_version(metadata, 'missing-ref')
    with pytest.raises(SystemExit):
        version_gate.extract_version(metadata, 'head', commit)
    with pytest.raises(SystemExit):
        version_gate.extract_version(metadata, 'base')


def test_migrating_to_static_metadata_keeps_every_version_law(historical_repo):
    metadata, commit = _commit(historical_repo)
    head = '[project]\nname="chances"\nversion="2.0.0"\n'
    assert version_gate.gate('feat!: add reproducible research', metadata, head, '',
                             '# v2.0.0\n\n- Add declared protocols.\n', base_ref=commit) == []
    failures = version_gate.gate('feat!: add reproducible research', metadata,
                                 head.replace('2.0.0', '0.2.0'), '',
                                 '# v0.2.0\n\n- Add declared protocols.\n', base_ref=commit)
    assert any('at least a major' in message for message in failures)
    failures = version_gate.gate('feat!: add reproducible research', metadata, head, '',
                                 '# v2.0.0\n\n- Added protocols.\n', base_ref=commit)
    assert any('past tense' in message for message in failures)


def test_source_symlink_is_rejected(historical_repo):
    repo = historical_repo
    metadata, _ = _commit(repo)
    path = repo / 'pkg/__init__.py'
    path.unlink()
    path.symlink_to('__version__ = "0.1.9"')
    subprocess.run(['git', 'add', '.'], cwd=repo, check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'test: forge source symlink'], cwd=repo, check=True)
    with pytest.raises(SystemExit):
        hatch_literal_version(metadata, 'HEAD')


def test_static_and_dynamic_metadata_cannot_conflict(historical_repo):
    metadata, commit = _commit(historical_repo)
    conflicting = metadata.replace('dynamic=["version"]', 'dynamic=["version"]\nversion="0.1.9"')
    for label in ('base', 'head'):
        with pytest.raises(SystemExit):
            version_gate.extract_version(conflicting, label, commit)


def test_workflow_passes_the_resolved_protected_base_revision():
    from _common import REPO_ROOT

    workflow = (REPO_ROOT / '.github/workflows/pr_checks_version.yml').read_text()
    assert '--base-ref "${{ steps.artifacts.outputs.base }}"' in workflow
    assert 'echo "base=$BASE_REV" >> "$GITHUB_OUTPUT"' in workflow
