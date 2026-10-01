"""Regressions for clean editable CI installs and Linux packaging dependencies."""

from __future__ import annotations

import re

import pytest
import yaml
from _common import REPO_ROOT, loads_toml
from _locked_requirements import locked_requirements
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

LOCKS = REPO_ROOT / 'requirements' / 'ci'
HASHED_SET = re.compile(r'--require-hashes -r requirements/ci/([a-z-]+)\.txt')
EDITABLE = re.compile(r'--no-build-isolation --no-deps -e \.(?:\s|$)')


def _active_requirements(name: str, python: str, platform: str) -> dict[str, Requirement]:
    environment = default_environment()
    environment.update(
        {
            'python_version': python,
            'python_full_version': f'{python}.20',
            'sys_platform': platform,
            'os_name': 'nt' if platform == 'win32' else 'posix',
            'platform_system': {'linux': 'Linux', 'darwin': 'Darwin', 'win32': 'Windows'}[platform],
            'platform_machine': 'x86_64',
            'platform_python_implementation': 'CPython',
            'implementation_name': 'cpython',
        }
    )
    requirements = locked_requirements((LOCKS / f'{name}.txt').read_text())
    return {
        canonicalize_name(requirement.name): requirement
        for requirement in requirements.values()
        if requirement.marker is None or requirement.marker.evaluate(environment)
    }


@pytest.mark.parametrize('name', ['build-tools', 'dev-env', 'product-env', 'minimum-env'])
@pytest.mark.parametrize('python', ['3.10', '3.12', '3.14'])
@pytest.mark.parametrize('platform', ['linux', 'darwin'])
def test_editable_backend_is_available_on_every_ci_target(
    name: str, python: str, platform: str
) -> None:
    dependencies = _active_requirements(name, python, platform)
    assert {'hatchling', 'editables'} <= dependencies.keys()
    assert Requirement('editables>=0.5,<1').specifier.contains(
        next(iter(dependencies['editables'].specifier)).version,
    )


def test_editable_jobs_install_the_locked_backend_before_building() -> None:
    editable_jobs: list[str] = []
    for workflow in sorted((REPO_ROOT / '.github' / 'workflows').glob('*.yml')):
        payload = yaml.safe_load(workflow.read_text())
        for job_name, job in payload['jobs'].items():
            installed: set[str] = set()
            for step in job.get('steps', []):
                program = step.get('run')
                if not isinstance(program, str):
                    continue
                for line in program.splitlines():
                    locked = HASHED_SET.search(line)
                    if locked:
                        installed.update(_active_requirements(locked[1], '3.12', 'linux'))
                    if EDITABLE.search(line):
                        editable_jobs.append(f'{workflow.name}:{job_name}')
                        assert {'hatchling', 'editables'} <= installed, editable_jobs[-1]
    assert editable_jobs, 'Expected CI to exercise clean editable installs.'


def test_linux_packaging_lock_contains_keyring_transitive_dependencies() -> None:
    linux = _active_requirements('packaging-tools', '3.12', 'linux')
    assert {
        'keyring',
        'secretstorage',
        'jeepney',
        'cryptography',
        'cffi',
        'pycparser',
    } <= linux.keys()
    macos = _active_requirements('packaging-tools', '3.12', 'darwin')
    assert 'keyring' in macos
    assert {'secretstorage', 'jeepney'}.isdisjoint(macos)


def test_editable_helper_is_not_a_scientific_runtime_dependency() -> None:
    runtime = _active_requirements('runtime-env', '3.12', 'linux')
    assert 'editables' not in runtime
    project = (REPO_ROOT / 'pyproject.toml').read_text()
    metadata = loads_toml(project)['project']
    assert 'editables' not in {Requirement(value).name for value in metadata['dependencies']}
    for extra in ('test', 'dev'):
        assert 'editables' in {
            Requirement(value).name for value in metadata['optional-dependencies'][extra]
        }


@pytest.mark.parametrize('platform', ['linux', 'darwin'])
def test_build_and_packaging_locks_share_one_coherent_tool_environment(platform: str) -> None:
    build = _active_requirements('build-tools', '3.12', platform)
    packaging = _active_requirements('packaging-tools', '3.12', platform)
    shared = build.keys() & packaging.keys()
    assert 'trove-classifiers' in shared, 'Expected the classifier library shared by Hatch and Pyroma.'
    conflicts = {
        name: (str(build[name].specifier), str(packaging[name].specifier))
        for name in shared
        if build[name].specifier != packaging[name].specifier
    }
    assert not conflicts, f'Combined hash-locked installation has conflicting pins: {conflicts}'
