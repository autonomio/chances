"""Release signatures must cover complete immutable source and distribution bytes."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('release_assets', ROOT / 'scripts/release_assets.py')
assert SPEC is not None and SPEC.loader is not None
ASSETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ASSETS)


@pytest.fixture
def repository(tmp_path, monkeypatch):
    """Use real Git archives, including hidden and non-package source files."""
    checkout = tmp_path / 'checkout'
    checkout.mkdir()
    for name, content in {
        'pyproject.toml': '[project]\nversion = "2.0.5"\n',
        '.github/workflows/release.yml': 'name: release\n',
        'chances/code.py': 'VALUE = 5\n', 'LICENSE': 'license fixture\n',
        'tests/test_code.py': 'assert 5 == 5\n',
    }.items():
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (checkout / 'source-link').symlink_to('LICENSE')
    subprocess.run(['git', 'init', '-q', str(checkout)], check=True)
    monkeypatch.setattr(ASSETS, 'ROOT', checkout)
    ASSETS.command('git', 'add', '.')
    ASSETS.command('git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
                   'commit', '-qm', 'fixture source')
    return checkout


def test_archive_contains_all_tracked_source_and_is_repeatable(repository, tmp_path):
    first, second = tmp_path / 'first.tar.gz', tmp_path / 'second.tar.gz'
    ASSETS.archive(first)
    (repository / 'untracked.txt').write_text('must not change approved source')
    (repository / 'pyproject.toml').write_text('[project]\nversion = "9.9.9"\n')
    (repository / 'chances/code.py').write_text('uncommitted worktree change')
    ASSETS.archive(second)
    assert first.read_bytes() == second.read_bytes()
    with tarfile.open(first) as source:
        assert {item.name for item in source if not item.isdir()} == {
            'chances-2.0.5/' + name for name in (
                'pyproject.toml', '.github/workflows/release.yml', 'chances/code.py',
                'LICENSE', 'tests/test_code.py', 'source-link',
            )
        }
        code = source.extractfile('chances-2.0.5/chances/code.py')
        assert code is not None and code.read() == b'VALUE = 5\n'


def test_archive_refuses_export_exclusions(repository, tmp_path):
    (repository / '.gitattributes').write_text('tests export-ignore\n')
    ASSETS.command('git', 'add', '.')
    ASSETS.command('git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.test',
                   'commit', '-qm', 'exclude tests')
    with pytest.raises(ValueError, match='every tracked file'):
        ASSETS.archive(tmp_path / 'source.tar.gz')
    assert not (tmp_path / 'source.tar.gz').exists()


def test_archive_refuses_checkout_writes(repository):
    with pytest.raises(ValueError, match='outside'):
        ASSETS.archive(repository / 'dirty.tar.gz')
    assert not (repository / 'dirty.tar.gz').exists()


@pytest.mark.parametrize('identical', [True, False])
def test_upload_compares_existing_bytes_before_any_mutation(tmp_path, monkeypatch, identical):
    existing, new = tmp_path / 'source.tar.gz', tmp_path / 'signature.json'
    existing.write_bytes(b'approved source')
    new.write_bytes(b'new signature')
    calls = []

    def command(*args):
        calls.append(args)
        if args[1:3] == ('release', 'view'):
            return json.dumps({'assets': [{'name': existing.name}]}).encode()
        if args[1:3] == ('release', 'download'):
            directory = Path(args[args.index('--dir') + 1])
            (directory / existing.name).write_bytes(b'approved source' if identical else b'tampered')
        return b''

    monkeypatch.setattr(ASSETS, 'command', command)
    if identical:
        ASSETS.upload('v2.0.5', [new, existing])
        assert calls[-1] == ('gh', 'release', 'upload', 'v2.0.5', str(new.resolve()))
    else:
        with pytest.raises(ValueError, match='Immutable release asset differs'):
            ASSETS.upload('v2.0.5', [new, existing])
        assert all(args[1:3] != ('release', 'upload') for args in calls)
    assert all('--clobber' not in args for args in calls)


def test_signing_and_source_verification_precede_release_mutations():
    release = yaml.safe_load((ROOT / '.github/workflows/pr_post_release.yml').read_text())
    job = release['jobs']['post_release']
    assert job['environment'] == 'release'
    assert job['permissions'] == {
        'contents': 'write', 'id-token': 'write', 'attestations': 'write',
    }
    names = [step['name'] for step in job['steps']]
    assert names.index('Verify source signing identity') < names.index('Create the approved tag and release')
    assert names.index('Create the approved tag and release') < names.index('Publish immutable source and signature bundle')
    verification = next(step for step in job['steps'] if step['name'] == 'Verify source signing identity')
    for flag in ('--source-digest "$GITHUB_SHA"', '--source-ref refs/heads/master',
                 '--deny-self-hosted-runners', '--signer-workflow', '--bundle "$SOURCE_BUNDLE"'):
        assert flag in verification['run']
