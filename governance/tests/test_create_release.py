"""Release mutations require verified master authorization and immutable tag targets."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('create_release', ROOT / 'scripts/create_release.py')
assert SPEC and SPEC.loader
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)
SHA = 'a' * 40


@pytest.fixture
def release_source(monkeypatch):
    for key, value in {'GITHUB_EVENT_NAME': 'workflow_dispatch',
                       'GITHUB_REF': 'refs/heads/master', 'GITHUB_SHA': SHA,
                       'GITHUB_REPOSITORY': 'autonomio/chances', 'REQUESTED_VERSION': '2.0.0'}.items():
        monkeypatch.setenv(key, value)
    commands = []
    responses = {
        ('git', 'remote', 'get-url', 'origin'): 'https://github.com/autonomio/chances.git',
        ('git', 'rev-parse', 'HEAD'): SHA,
        ('git', 'ls-remote', 'origin', 'refs/heads/master'): SHA + '\trefs/heads/master',
        ('git', 'status', '--porcelain'): '',
    }

    def run(*args):
        commands.append(args)
        return responses.get(args, '')

    monkeypatch.setattr(RELEASE, 'run', run)
    return responses, commands


@pytest.mark.parametrize(('key', 'value'), [
    ('GITHUB_EVENT_NAME', 'push'), ('GITHUB_REF', 'refs/tags/v2.0.0'),
    ('GITHUB_SHA', 'b' * 40), ('GITHUB_REPOSITORY', 'foreign/project'),
])
def test_wrong_authorization_fails_before_mutations(release_source, monkeypatch, key, value):
    _, commands = release_source
    monkeypatch.setenv(key, value)
    with pytest.raises(SystemExit):
        RELEASE.main()
    assert not any(command[:2] in {('git', 'tag'), ('git', 'push'), ('gh', 'release')}
                   for command in commands)


@pytest.mark.parametrize(('command', 'response'), [
    (('git', 'status', '--porcelain'), ' M chances/_api.py'),
    (('git', 'ls-remote', 'origin', 'refs/heads/master'), 'b' * 40 + '\trefs/heads/master'),
    (('git', 'ls-remote', 'origin', 'refs/heads/master'), ''),
])
def test_dirty_or_stale_source_fails_closed(release_source, command, response):
    responses, _ = release_source
    responses[command] = response
    with pytest.raises(SystemExit):
        RELEASE.approved_source('autonomio/chances')


@pytest.mark.parametrize(('local', 'remote'), [(None, 'b' * 40), ('b' * 40, None)])
def test_existing_tag_cannot_be_moved(release_source, monkeypatch, local, remote):
    _, commands = release_source
    monkeypatch.setattr(RELEASE, 'current_version', lambda: '2.0.0')
    monkeypatch.setattr(RELEASE, 'newest_changelog_section', lambda version: 'Add scientific receipts.')
    monkeypatch.setattr(RELEASE, 'tag_targets', lambda tag: (local, remote))
    with pytest.raises(SystemExit, match=r'existing v2\.0\.0'):
        RELEASE.main()
    assert ('git', 'push', 'origin', 'refs/tags/v2.0.0') not in commands


def test_partial_remote_tag_resumes_release_without_tag_mutation(release_source, monkeypatch):
    _, commands = release_source
    monkeypatch.setattr(RELEASE, 'current_version', lambda: '2.0.0')
    monkeypatch.setattr(RELEASE, 'newest_changelog_section', lambda version: 'Add scientific receipts.')
    monkeypatch.setattr(RELEASE, 'tag_targets', lambda tag: (None, SHA))
    monkeypatch.setattr(RELEASE, 'release_exists', lambda repo, tag: False)
    assert RELEASE.main() == 0
    assert not any(command[:2] in {('git', 'push'), ('git', 'tag')} for command in commands
                   if command[2:3] != ('--list',))
    publication = next(command for command in commands if command[:3] == ('gh', 'release', 'create'))
    assert '--verify-tag' in publication and publication[publication.index('--repo') + 1] == 'autonomio/chances'
