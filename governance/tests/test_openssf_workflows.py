"""Security tooling keeps default tokens read-only and badge claims attributable."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
import yaml
from _common import loads_toml
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = tuple(sorted((ROOT / '.github/workflows').glob('*.yml')))


@pytest.mark.parametrize('path', WORKFLOWS, ids=lambda path: path.stem)
def test_workflow_defaults_cannot_grant_write(path: Path) -> None:
    """Default permissions cannot silently propagate mutation to later jobs."""
    workflow = yaml.safe_load(path.read_text())
    permissions = workflow['permissions']
    assert isinstance(permissions, dict), path
    assert all(value in {'read', 'none'} for value in permissions.values()), path


def test_mutation_permissions_remain_explicit_in_their_jobs() -> None:
    """Least privilege must preserve required gate delivery and publication."""
    expected = {
        'bootstrap_repository.yml': ('bootstrap', {'contents', 'issues', 'pull-requests'}),
        'copy-standard-labels.yml': ('setup', {'issues'}),
        'pr_checks_slice_on_issue.yml': ('rerun_slice_gate_for_linked_prs', {'checks', 'actions'}),
        'pr_checks_slice_sweep.yml': ('sweep_slice_gate_for_open_prs', {'checks'}),
    }
    for filename, (job, writable) in expected.items():
        workflow = yaml.safe_load((ROOT / '.github/workflows' / filename).read_text())
        permissions = workflow['jobs'][job]['permissions']
        assert {key for key, value in permissions.items() if value == 'write'} == writable


def test_badge_proposals_require_explicit_evidence() -> None:
    """Published statuses retain evidence and distinguish human attestations."""
    proposals = json.loads((ROOT / '.bestpractices.json').read_text())
    assert proposals['release_notes_vulns_status'] == 'N/A'
    assert 'public records' in proposals['release_notes_vulns_justification']
    for criterion in ('know_secure_design', 'know_common_errors', 'no_leaked_credentials'):
        assert 'confirmed on 2026-10-01' in proposals[f'{criterion}_justification']
    for key, value in proposals.items():
        if key.endswith('_status'):
            assert value in {'Met', 'Unmet', 'N/A', '?'}
            justification = proposals.get(key.removesuffix('_status') + '_justification')
            assert isinstance(justification, str) and justification.strip()


def test_fuzzing_uses_bounded_locked_tooling() -> None:
    """A fuzz marker counts only when CI runs a constrained real campaign."""
    for filename in ('fuzz.yml', 'pr_checks_lint.yml'):
        workflow = yaml.safe_load((ROOT / '.github/workflows' / filename).read_text())
        commands = '\n'.join(step.get('run', '') for job in workflow['jobs'].values()
                             for step in job['steps'])
        assert '--require-hashes' in commands
        assert 'requirements/ci/fuzz-env.txt' in commands
        assert 'fuzz/fuzz_protocol.py' in commands
        assert '-atheris_runs=10000' in commands
        assert '-max_len=4096' in commands
    assert 'atheris==' in (ROOT / 'requirements/ci/fuzz-env.txt').read_text()
    assert 'atheris.Setup(' in (ROOT / 'fuzz/fuzz_protocol.py').read_text()


def test_runtime_requirements_preserve_project_envelope() -> None:
    """Scanner-compatible requirements must not widen the supported runtime."""
    project = loads_toml((ROOT / 'pyproject.toml').read_text())
    expected = {Requirement(value).name: Requirement(value).specifier
                for value in project['project']['dependencies']}
    constraints = {Requirement(line).name: Requirement(line).specifier
                   for line in (ROOT / 'requirements/constraints.txt').read_text().splitlines()
                   if line.strip() and not line.startswith('#')}
    lines = (ROOT / 'requirements.txt').read_text().splitlines()
    assert '-c requirements/constraints.txt' in lines
    declared = [Requirement(line) for line in lines
                if line.strip() and not line.startswith(('#', '-'))]
    assert {requirement.name for requirement in declared} == expected.keys()
    for requirement in declared:
        effective = SpecifierSet(f'{requirement.specifier},{constraints[requirement.name]}')
        assert effective == expected[requirement.name]
    assert '/requirements/constraints.txt' in project['tool']['hatch']['build']['targets']['sdist']['include']


def test_declared_version_matches_package_and_citation() -> None:
    """Source exports, package artifacts and citation metadata advance together."""
    version = loads_toml((ROOT / 'pyproject.toml').read_text())['project']['version']
    module = ast.parse((ROOT / 'chances/__init__.py').read_text())
    declared = next(node.value for node in module.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == '__version__'
                            for target in node.targets))
    assert ast.literal_eval(declared) == version
    assert yaml.safe_load((ROOT / 'CITATION.cff').read_text())['version'] == version
