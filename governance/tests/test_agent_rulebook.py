"""Pin the adopted Chances review policy and validate its repository appendix.

The operator specialized upstream wording for this repository. The digest
binds that adopted artifact, not a claim of organization-wide provenance.
"""

from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PR_GUIDELINE = REPO_ROOT / 'AUTONOMIO_PR_GUIDELINE.md'
REPO_SPECIFICS = REPO_ROOT / 'AUTONOMIO_REPO_SPECIFICS.md'
EXPECTED_PR_GUIDELINE_SHA256 = 'd7ccdbdc4effaba96df81b1b49d657065a289454b2ef625db1f1da841f763322'

# Tokens the bootstrap rename engine rewrites. A file carrying any of them
# cannot also carry a byte pin.
#
# Assembled rather than written as literals: this file is itself inside the
# rewrite sweep, so a literal `new_repository_template` here becomes the
# derived repository's own package name and the check silently stops looking
# for the thing it was written to find. The seed names come from the bootstrap
# module, which is the one file the sweep skips.
_SEEDS = frozenset({'new' + '_repository_' + 'template', 'new' + '-repository-' + 'template'})
REWRITTEN_TOKENS = tuple(sorted(_SEEDS)) + tuple(
    '{' + name + '}'
    for name in ('REPOSITORY_NAME', 'DISPLAY_NAME', 'REPOSITORY_OWNER')
)


def test_autonomio_pr_guideline_is_posted_unchanged() -> None:
    """Verify the universal PR guideline exists with the canonical digest."""
    assert PR_GUIDELINE.is_file()
    assert sha256(PR_GUIDELINE.read_bytes()).hexdigest() == EXPECTED_PR_GUIDELINE_SHA256


def test_the_pinned_guideline_carries_no_rewritable_token() -> None:
    """A byte pin is only safe on a file bootstrap leaves alone.

    This is the assertion that would have caught the appendix being pinned. If
    the guideline ever gains the template's own slug or package name, bootstrap
    rewrites it and the digest above fails in every derived repository, inside
    a required check, before the bootstrap PR can merge.
    """
    text = PR_GUIDELINE.read_text(encoding='utf-8')
    for token in REWRITTEN_TOKENS:
        assert token not in text, (
            f'{PR_GUIDELINE.name} contains {token!r}, which bootstrap rewrites. '
            f'A rewritten file cannot carry a byte pin: every derived repository '
            f'would fail this test in a required check.'
        )


def test_repo_specifics_exists_and_points_at_the_guideline() -> None:
    """The appendix must remain an appendix, whatever its entries say."""
    assert REPO_SPECIFICS.is_file()
    assert 'AUTONOMIO_PR_GUIDELINE.md' in REPO_SPECIFICS.read_text(encoding='utf-8')


def test_repo_specifics_carries_scoped_entries() -> None:
    """Its entries stay `[repo:<scope>]`-tagged, which is what makes it usable.

    Checked as shape rather than as bytes: the content is per-repository by
    definition, and pinning those bytes is what broke every derived repository.
    """
    text = REPO_SPECIFICS.read_text(encoding='utf-8')
    assert re.search(r'^- `\[repo:[^\]]+\]`', text, re.MULTILINE), (
        'the appendix carries no `[repo:<scope>]` entries'
    )


def test_adopted_guideline_preserves_repository_scope_and_authorization() -> None:
    text = PR_GUIDELINE.read_text()
    assert 'Scope: Autonomio/Chances.' in text
    assert 'No organization-wide policy is asserted.' in text
    assert 'Publication and messaging follow operator authorization.' in text
    for rule in ('[change:typing]', '[change:exceptions]', '[evidence:performance]',
                 '[docs:single-source]', '[review:diff-plus]'):
        assert rule in text
