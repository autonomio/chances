"""Bound obsolete CI demand while retaining every scientific and required check."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_source_checks_are_bounded_without_losing_required_gates():
    workflows = []
    for path in (ROOT / '.github/workflows').glob('*.yml'):
        document = yaml.safe_load(path.read_text())
        triggers = document.get(True, {})
        if 'pull_request' in triggers and path.name != 'pr_merge_readiness.yml':
            workflows.append(document)
            concurrency = document['concurrency']
            assert concurrency['cancel-in-progress'] is True, path.name
            assert 'github.workflow' in concurrency['group'], path.name
            assert 'github.ref' in concurrency['group'], path.name
            for name, job in document['jobs'].items():
                assert 1 <= job['timeout-minutes'] <= 30, (path.name, name)
        if 'push' in triggers:
            assert triggers['push']['branches'] == ['master'], path.name
    jobs = {job['name'] for document in workflows for job in document['jobs'].values()}
    assert {
        'pr_checks_slice', 'pr_checks_cc', 'pr_checks_typing', 'pr_checks_fail_loud',
        'pr_checks_version', 'pr_checks_lint', 'pr_checks_tests', 'PR Checks CodeQL',
        'pr_checks_honesty', 'pr_checks_ruleset',
    } <= jobs
    packaging = yaml.safe_load((ROOT / '.github/workflows/pr_checks_packaging.yml').read_text())
    assert packaging['jobs']['pr_checks_package_install']['strategy']['matrix']['python-version'] == [
        '3.10', '3.12', '3.14',
    ]


def test_dependency_updates_retain_security_handling_without_weekly_bursts():
    updates = yaml.safe_load((ROOT / '.github/dependabot.yml').read_text())['updates']
    assert len({item['schedule']['day'] for item in updates}) == len(updates)
    for item in updates:
        assert item['open-pull-requests-limit'] == 1
        assert {group['applies-to'] for group in item['groups'].values()} == {
            'security-updates', 'version-updates',
        }
        assert 'ignore' not in item


def test_readiness_skips_empty_suites_before_allocating_a_runner():
    workflow = yaml.safe_load((ROOT / '.github/workflows/pr_merge_readiness.yml').read_text())
    assert workflow['jobs']['report_merge_readiness']['if'] == (
        "${{ github.event_name != 'check_suite' || github.event.check_suite.pull_requests[0] != null }}"
    )
    assert workflow['concurrency']['cancel-in-progress'] is False
