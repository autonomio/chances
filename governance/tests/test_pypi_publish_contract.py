"""Publication stays manually approved, token-explicit, and isolated from builds."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / '.github/workflows/pr_publish_pypi.yml'
REQUEST = 'Validate explicit publication request'
TOKEN = 'Validate the configured PyPI API token'
HISTORY = 'Validate released version and protected history'


@pytest.fixture
def workflow():
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding='utf-8'))


def _step(workflow, job, name):
    return next(item for item in workflow['jobs'][job]['steps'] if item['name'] == name)


def _run_guard(workflow, job, name, environment, directory):
    return subprocess.run(
        ['/bin/bash', '-c', _step(workflow, job, name)['run']],
        env={'PATH': os.defpath, **environment}, cwd=directory,
        capture_output=True, text=True, check=False, timeout=10,
    )


def test_publication_requires_manual_dispatch_and_separate_environment_approvals(workflow):
    # PyYAML follows YAML 1.1 and reads the Actions "on" key as True.
    assert set(workflow[True]) == {'workflow_dispatch'}
    assert workflow[True]['workflow_dispatch']['inputs']['tag']['required'] is True
    assert workflow['concurrency']['cancel-in-progress'] is False
    jobs = workflow['jobs']
    assert jobs['build_distribution']['environment'] == 'release'
    assert jobs['publish_to_pypi']['environment'] == 'pypi'
    assert jobs['publish_to_pypi']['needs'] == 'build_distribution'
    assert jobs['publish_to_pypi']['permissions'] == {}
    checkout = _step(workflow, 'build_distribution', 'Checkout the approved release tag')
    assert checkout['with']['ref'] == '${{ inputs.tag }}'
    assert checkout['with']['persist-credentials'] is False


def test_publication_uses_only_explicit_token_without_oidc_or_package_build(workflow):
    build = workflow['jobs']['build_distribution']
    publish = workflow['jobs']['publish_to_pypi']
    assert build['permissions'] == {
        'contents': 'write', 'id-token': 'write', 'attestations': 'write',
    }
    assert '${{ secrets.PYPI_API_TOKEN }}' not in json.dumps(build)
    steps = publish['steps']
    assert [item['name'] for item in steps] == [
        TOKEN, 'Download approved distributions', 'Publish with the organization PyPI API token',
    ]
    assert steps[0]['env'] == {'PYPI_API_TOKEN': '${{ secrets.PYPI_API_TOKEN }}'}
    assert steps[2]['uses'] == (
        'pypa/gh-action-pypi-publish@ed0c53931b1dc9bd32cbe73a98c7f6766f8a527e'
    )
    assert steps[2]['with'] == {
        'user': '__token__', 'password': '${{ secrets.PYPI_API_TOKEN }}', 'attestations': False,
    }
    assert 'PYPI_USERNAME' not in json.dumps(publish)
    assert 'PYPI_PASSWORD' not in json.dumps(publish)
    upload = _step(workflow, 'build_distribution', 'Upload distributions')
    assert upload['with']['name'] == steps[1]['with']['name'] == 'pypi-distributions'
    assert upload['with']['if-no-files-found'] == 'error'
    assert _step(workflow, 'build_distribution', 'Attest build provenance')['with'] == {
        'subject-path': 'dist/*',
    }
    assert 'sha256sum' in _step(workflow, 'build_distribution', 'Record artifact digests')['run']


@pytest.mark.parametrize(('key', 'value'), [
    ('PUBLISH_REF', 'refs/heads/unreviewed'), ('PUBLISH_REF', 'refs/tags/v2.0.0'),
    ('PUBLISH_ENABLED', ''), ('PUBLISH_ENABLED', 'false'), ('PUBLISH_ENABLED', 'TRUE'),
    ('RELEASE_TAG', '2.0.0'), ('RELEASE_TAG', 'v2.0'), ('RELEASE_TAG', 'v2.0.0rc1'),
    ('RELEASE_TAG', 'v2.0.0\n'), ('RELEASE_TAG', 'v2.0.0; touch injected'),
])
def test_request_guard_rejects_unapproved_inputs(workflow, tmp_path, key, value):
    environment = {
        'PUBLISH_REF': 'refs/heads/master', 'PUBLISH_ENABLED': 'true', 'RELEASE_TAG': 'v2.0.0',
    }
    environment[key] = value
    result = _run_guard(workflow, 'build_distribution', REQUEST, environment, tmp_path)
    assert result.returncode != 0
    assert '::error::' in result.stdout
    assert not (tmp_path / 'injected').exists()


def test_request_guard_accepts_explicit_master_enabled_semver_tag(workflow, tmp_path):
    result = _run_guard(workflow, 'build_distribution', REQUEST, {
        'PUBLISH_REF': 'refs/heads/master', 'PUBLISH_ENABLED': 'true', 'RELEASE_TAG': 'v2.0.0',
    }, tmp_path)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ''


@pytest.mark.parametrize('token', ['', 'password-fixture', 'ghp-unrelated-token', ' pypi-fixture'])
def test_token_guard_rejects_missing_or_wrong_credentials_without_leaking(workflow, tmp_path, token):
    result = _run_guard(workflow, 'publish_to_pypi', TOKEN, {'PYPI_API_TOKEN': token}, tmp_path)
    assert result.returncode != 0
    assert '::error::' in result.stdout
    if token:
        assert token not in result.stdout + result.stderr


@pytest.mark.parametrize('token', ['pypi-explicit-test-fixture', 'pypi-$(touch injected)'])
def test_token_guard_accepts_fixture_without_printing_or_executing_it(workflow, tmp_path, token):
    result = _run_guard(workflow, 'publish_to_pypi', TOKEN, {'PYPI_API_TOKEN': token}, tmp_path)
    assert result.returncode == 0
    assert result.stdout == result.stderr == ''
    assert not (tmp_path / 'injected').exists()


@pytest.mark.parametrize(('project', 'version', 'ancestor', 'release', 'accepted'), [
    ('chances', '2.0.0', '0', {'tagName': 'v2.0.0', 'isDraft': False, 'isPrerelease': False}, True),
    ('foreign', '2.0.0', '0', {'tagName': 'v2.0.0', 'isDraft': False, 'isPrerelease': False}, False),
    ('chances', '2.0.1', '0', {'tagName': 'v2.0.0', 'isDraft': False, 'isPrerelease': False}, False),
    ('chances', '2.0.0', '1', {'tagName': 'v2.0.0', 'isDraft': False, 'isPrerelease': False}, False),
    ('chances', '2.0.0', '0', {'tagName': 'v2.0.1', 'isDraft': False, 'isPrerelease': False}, False),
    ('chances', '2.0.0', '0', {'tagName': 'v2.0.0', 'isDraft': True, 'isPrerelease': False}, False),
    ('chances', '2.0.0', '0', {'tagName': 'v2.0.0', 'isDraft': False, 'isPrerelease': True}, False),
])
def test_history_guard_requires_this_project_version_protected_ancestry_and_final_release(
    workflow, tmp_path, project, version, ancestor, release, accepted,
):
    tools = tmp_path / 'tools'
    tools.mkdir()
    (tools / 'python').symlink_to(sys.executable)
    for name, script in {
        'git': '#!/bin/sh\nif [ "$*" = "rev-parse HEAD" ]; then printf "%s" "$CHECKOUT_SHA"; exit 0; fi\n[ "$*" = "merge-base --is-ancestor HEAD origin/master" ] || exit 90\nexit "$ANCESTOR_RESULT"\n',
        'gh': '#!/bin/sh\nprintf "%s" "$RELEASE_JSON"\n',
    }.items():
        executable = tools / name
        executable.write_text(script, encoding='utf-8')
        executable.chmod(0o700)
    (tmp_path / 'pyproject.toml').write_text(
        f'[project]\nname = "{project}"\nversion = "{version}"\n', encoding='utf-8',
    )
    result = _run_guard(workflow, 'build_distribution', HISTORY, {
        'PATH': str(tools) + os.pathsep + os.defpath, 'RELEASE_TAG': 'v2.0.0',
        'GITHUB_REPOSITORY': 'autonomio/chances', 'ANCESTOR_RESULT': ancestor,
        'RELEASE_JSON': json.dumps(release), 'GITHUB_SHA': 'a' * 40, 'CHECKOUT_SHA': 'a' * 40,
    }, tmp_path)
    assert (result.returncode == 0) is accepted


def test_history_guard_rejects_checkout_that_differs_from_dispatch(workflow, tmp_path):
    tools = tmp_path / 'tools'
    tools.mkdir()
    (tools / 'python').symlink_to(sys.executable)
    git = tools / 'git'
    git.write_text('#!/bin/sh\n[ "$*" = "rev-parse HEAD" ] || exit 90\nprintf "%s" "$CHECKOUT_SHA"\n')
    git.chmod(0o700)
    (tmp_path / 'pyproject.toml').write_text('[project]\nname="chances"\nversion="2.0.0"\n')
    result = _run_guard(workflow, 'build_distribution', HISTORY, {
        'PATH': str(tools) + os.pathsep + os.defpath, 'RELEASE_TAG': 'v2.0.0',
        'GITHUB_SHA': 'a' * 40, 'CHECKOUT_SHA': 'b' * 40,
    }, tmp_path)
    assert result.returncode != 0
    assert 'differs from dispatch SHA' in result.stdout
    assert not (tmp_path / 'release.json').exists()


def test_source_provenance_is_checked_before_build_and_pypi_handoff(workflow):
    steps = workflow['jobs']['build_distribution']['steps']
    names = [step['name'] for step in steps]
    assert names.index(HISTORY) < names.index('Verify authenticated complete release source')
    assert names.index('Verify authenticated complete release source') < names.index('Build and audit distributions')
    assert names.index('Publish immutable distributions and signature bundle') < names.index('Upload distributions')
    for name, signer in [
        ('Verify authenticated complete release source', 'pr_post_release.yml'),
        ('Publish immutable distributions and signature bundle', 'pr_publish_pypi.yml'),
    ]:
        program = _step(workflow, 'build_distribution', name)['run']
        for flag in ('--source-digest "$GITHUB_SHA"', '--source-ref refs/heads/master',
                     '--deny-self-hosted-runners', '--signer-workflow'):
            assert flag in program
        assert signer in program
    assert 'cmp ' in _step(workflow, 'build_distribution', 'Verify authenticated complete release source')['run']
