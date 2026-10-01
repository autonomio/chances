"""Require bit-mis approval for every PR through sole global code ownership.

The protected default branch supplies CODEOWNERS and the ruleset enforces owner
review outside the judged merge ref. No later path rule may substitute another
owner. PR authors cannot approve themselves; last-push approval independently
requires a reviewer other than the latest reviewable pusher. Approval count alone
does not select the designated operator.
"""
from __future__ import annotations

import json

import yaml
from _common import REPO_ROOT

CODEOWNERS = REPO_ROOT / '.github' / 'CODEOWNERS'
RULESET_SNAPSHOT = REPO_ROOT / '.github' / 'rulesets' / 'main.json'
ENFORCEMENT_PATHS = frozenset({
    '/CLAUDE.md',
    '/governance/',
    '/.github/',
    '/governance.yml',
    '/pyproject.toml',
    '/requirements/',
    '/AGENTS.md',
    '/SETUP.md',
    '/docs/Developer/',
    '/docs-site/',
    '/scripts/',
    '/tests/package/conftest.py',
})
GOVERNANCE_CONFIG = REPO_ROOT / 'governance.yml'


def _rule_lines() -> list[list[str]]:
    lines = []
    for raw in CODEOWNERS.read_text(encoding='utf-8').splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith('#'):
            lines.append(stripped.split())
    return lines


def test_codeowners_requires_bit_mis_for_every_path() -> None:
    assert _rule_lines() == [['*', '@bit-mis']], (
        'every path must require bit-mis without later ownership overrides'
    )


def test_enforcement_surfaces_resolve_on_disk() -> None:
    for pattern in ENFORCEMENT_PATHS:
        target = REPO_ROOT / pattern.lstrip('/').rstrip('/')
        if pattern.endswith('/'):
            assert target.is_dir(), f'{pattern} does not resolve to a directory'
        else:
            assert target.is_file(), f'{pattern} does not resolve to a file'


def test_governance_names_bit_mis_as_approving_authority() -> None:
    config = yaml.safe_load(GOVERNANCE_CONFIG.read_text(encoding='utf-8'))
    assert config['review']['approving_authority'] == 'bit-mis'


def test_ruleset_snapshot_requires_code_owner_review() -> None:
    snapshot = json.loads(RULESET_SNAPSHOT.read_text(encoding='utf-8'))
    params = [
        rule['parameters']
        for rule in snapshot['rules']
        if rule['type'] == 'pull_request'
    ]
    assert [p['require_code_owner_review'] for p in params] == [True]
    # The most recent reviewable push needs approval from another user;
    # code-owner review independently makes bit-mis a required approver.
    assert [p['require_last_push_approval'] for p in params] == [True]
    assert [p['required_approving_review_count'] for p in params] == [1]
