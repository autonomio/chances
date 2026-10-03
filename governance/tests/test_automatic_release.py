"""Automatic publication requires successful matching master verification."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SHA = 'a' * 40


@pytest.fixture
def automatic_request(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="chances"\nversion="2.0.7"\n')
    tools = tmp_path / 'tools'
    tools.mkdir()
    git = tools / 'git'
    git.write_text('#!/bin/sh\n[ "$*" = "ls-remote --tags origin refs/tags/v2.0.7 refs/tags/v2.0.7^{}" ] || exit 90\nprintf "%s" "$REMOTE_TAGS"\n')
    git.chmod(0o700)
    event = {'workflow_run': {
        'name': 'Verify and build', 'status': 'completed', 'conclusion': 'success',
        'event': 'push', 'head_branch': 'master', 'head_sha': SHA,
        'head_repository': {'full_name': 'autonomio/chances'},
    }}
    environment = {
        'PATH': str(tools) + os.pathsep + os.defpath,
        'GITHUB_EVENT_PATH': str(tmp_path / 'event.json'),
        'GITHUB_EVENT_NAME': 'workflow_run', 'GITHUB_REF': 'refs/heads/master',
        'GITHUB_SHA': SHA, 'GITHUB_REPOSITORY': 'autonomio/chances',
        'GITHUB_OUTPUT': str(tmp_path / 'outputs'),
        'REMOTE_TAGS': '',
    }
    return tmp_path, event, environment


def run_request(automatic_request, mode='release'):
    directory, event, environment = automatic_request
    Path(environment['GITHUB_EVENT_PATH']).write_text(json.dumps(event))
    return subprocess.run([sys.executable, str(ROOT / 'scripts/release_request.py'), mode],
                          env=environment, cwd=directory, text=True, capture_output=True,
                          check=False, timeout=10)


def test_successful_master_version_change_resolves_release(automatic_request):
    assert run_request(automatic_request).returncode == 0
    assert (automatic_request[0] / 'outputs').read_text() == 'version=2.0.7\ntag=v2.0.7\nready=true\n'


@pytest.mark.parametrize(('key', 'value'), [
    ('name', 'Unrelated workflow'), ('status', 'in_progress'), ('conclusion', 'failure'),
    ('event', 'pull_request'), ('head_branch', 'feature'), ('head_sha', 'b' * 40),
    ('head_repository', {'full_name': 'foreign/chances'}),
])
def test_untrusted_or_stale_upstream_cannot_create_outputs(automatic_request, key, value):
    automatic_request[1]['workflow_run'][key] = value
    result = run_request(automatic_request)
    assert result.returncode != 0
    assert not (automatic_request[0] / 'outputs').exists()


@pytest.mark.parametrize('mode', ['release', 'publish'])
def test_unchanged_version_skips_entire_automatic_chain(automatic_request, mode):
    _, event, environment = automatic_request
    environment['REMOTE_TAGS'] = 'b' * 40 + '\trefs/tags/v2.0.7\n'
    if mode == 'publish':
        event['workflow_run'].update(name='Approved Release', event='workflow_run')
    assert run_request(automatic_request, mode).returncode == 0
    assert 'ready=false' in Path(environment['GITHUB_OUTPUT']).read_text()


def test_publication_requires_successful_release_for_same_commit(automatic_request):
    assert run_request(automatic_request, 'publish').returncode != 0
    automatic_request[1]['workflow_run'].update(name='Approved Release', event='workflow_run')
    automatic_request[2]['REMOTE_TAGS'] = SHA + '\trefs/tags/v2.0.7\n'
    assert run_request(automatic_request, 'publish').returncode == 0
    assert 'ready=true' in (automatic_request[0] / 'outputs').read_text()


@pytest.mark.parametrize(('mode', 'inputs', 'accepted'), [
    ('release', {'version': '2.0.7'}, True), ('release', {'version': '2.0.6'}, False),
    ('publish', {'tag': 'v2.0.7'}, True), ('publish', {'tag': 'v2.0.6'}, False),
])
def test_manual_recovery_keeps_exact_version_identity(automatic_request, mode, inputs, accepted):
    _, event, environment = automatic_request
    event.clear()
    event['inputs'] = inputs
    environment['GITHUB_EVENT_NAME'] = 'workflow_dispatch'
    assert (run_request(automatic_request, mode).returncode == 0) is accepted


def test_release_pipeline_has_no_credentialed_work_before_request_validation():
    for name, upstream, job in [
        ('pr_post_release.yml', 'Verify and build', 'post_release'),
        ('pr_publish_pypi.yml', 'Approved Release', 'build_distribution'),
    ]:
        workflow = yaml.safe_load((ROOT / '.github/workflows' / name).read_text())
        assert workflow[True]['workflow_run'] == {
            'workflows': [upstream], 'types': ['completed'], 'branches': ['master'],
        }
        assert workflow['jobs']['prepare_request']['permissions'] == {'contents': 'read'}
        assert workflow['jobs'][job]['needs'] == 'prepare_request'
        assert workflow['jobs'][job]['if'] == "${{ needs.prepare_request.outputs.ready == 'true' }}"


def test_release_git_receives_authorization_header_exactly_once(tmp_path):
    workflow = yaml.safe_load((ROOT / '.github/workflows/pr_post_release.yml').read_text())
    step = next(item for item in workflow['jobs']['post_release']['steps']
                if item['name'] == 'Create the approved tag and release')
    for name, source in {
        'git': '#!/bin/sh\nprintf "%s\\n" "$GIT_CONFIG_COUNT|$GIT_CONFIG_KEY_0|$*" > "$CAPTURE"\n',
        'python': '#!/bin/sh\nexit 0\n',
    }.items():
        file = tmp_path / name
        file.write_text(source)
        file.chmod(0o700)
    capture = tmp_path / 'git-call'
    result = subprocess.run(['/bin/bash', '-c', step['run']], cwd=tmp_path, check=False,
                            capture_output=True, text=True, timeout=10,
                            env={'PATH': str(tmp_path) + os.pathsep + os.defpath,
                                 'GH_TOKEN': 'fixture-token', 'CAPTURE': str(capture)})
    assert result.returncode == 0
    assert capture.read_text().strip() == '1|http.https://github.com/.extraheader|fetch origin master --tags'


def test_version_bump_before_merge_tail_still_releases(automatic_request):
    directory, event, environment = automatic_request
    environment['PATH'] = os.defpath

    def git(*arguments):
        return subprocess.run(['git', '-C', str(directory), *arguments], check=True,
                              capture_output=True, text=True, timeout=10).stdout.strip()

    git('init', '-q', '--initial-branch=master')
    git('config', 'user.name', 'Fixture')
    git('config', 'user.email', 'fixture@example.test')
    (directory / 'pyproject.toml').write_text('[project]\nname="chances"\nversion="2.0.6"\n')
    git('add', 'pyproject.toml')
    git('commit', '-qm', 'baseline')
    (directory / 'pyproject.toml').write_text('[project]\nname="chances"\nversion="2.0.7"\n')
    git('add', 'pyproject.toml')
    git('commit', '-qm', 'bump version')
    (directory / 'notes').write_text('final reviewed increment')
    git('add', 'notes')
    git('commit', '-qm', 'merge tail')
    git('init', '--bare', str(directory / 'remote.git'))
    git('remote', 'add', 'origin', str(directory / 'remote.git'))
    environment['GITHUB_SHA'] = git('rev-parse', 'HEAD')
    event['workflow_run']['head_sha'] = environment['GITHUB_SHA']
    assert 'version="2.0.7"' in git('show', 'HEAD^:pyproject.toml')
    assert run_request(automatic_request).returncode == 0
    assert 'ready=true' in (directory / 'outputs').read_text()


@pytest.mark.parametrize(('mode', 'target', 'accepted', 'ready'), [
    ('release', '', True, True), ('release', SHA, True, True),
    ('release', 'b' * 40, True, False), ('publish', '', False, False),
    ('publish', SHA, True, True), ('publish', 'b' * 40, True, False),
])
def test_annotated_tag_identity_controls_retries(automatic_request, mode, target, accepted, ready):
    _, event, environment = automatic_request
    if target:
        environment['REMOTE_TAGS'] = ('c' * 40 + '\trefs/tags/v2.0.7\n'
                                      + target + '\trefs/tags/v2.0.7^{}\n')
    if mode == 'publish':
        event['workflow_run'].update(name='Approved Release', event='workflow_run')
    assert (run_request(automatic_request, mode).returncode == 0) is accepted
    if accepted:
        assert f'ready={str(ready).lower()}' in Path(environment['GITHUB_OUTPUT']).read_text()
    else:
        assert not Path(environment['GITHUB_OUTPUT']).exists()


@pytest.mark.parametrize('version', ['2.0', '2.0.7rc1', ' 2.0.7', '2.0.7\nready=true'])
def test_malformed_version_cannot_inject_workflow_outputs(automatic_request, version):
    directory = automatic_request[0]
    (directory / 'pyproject.toml').write_text(f'[project]\nname="chances"\nversion={json.dumps(version)}\n')
    assert run_request(automatic_request).returncode != 0
    assert not (directory / 'outputs').exists()
