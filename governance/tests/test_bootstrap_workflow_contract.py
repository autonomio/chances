from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_WORKFLOW = REPO_ROOT / '.github/workflows/bootstrap_repository.yml'
LINT_WORKFLOW = REPO_ROOT / '.github/workflows/pr_checks_lint.yml'
RULESET_WORKFLOW = REPO_ROOT / '.github/workflows/pr_checks_ruleset.yml'
TYPING_WORKFLOW = REPO_ROOT / '.github/workflows/pr_checks_typing.yml'
VERSION_WORKFLOW = REPO_ROOT / '.github/workflows/pr_checks_version.yml'
FAIL_LOUD_WORKFLOW = REPO_ROOT / '.github/workflows/pr_checks_fail_loud.yml'
BOOTSTRAP_SCRIPT = REPO_ROOT / 'governance/bootstrap_repository.py'


def test_bootstrap_uses_pr_path_for_protected_main() -> None:
    workflow = BOOTSTRAP_WORKFLOW.read_text(encoding='utf-8')

    assert 'REPO_BOOTSTRAP_TOKEN is required' in workflow
    assert 'push origin "HEAD:${BOOTSTRAP_BRANCH}"' in workflow
    assert 'http.https://github.com/.extraheader=$AUTH' in workflow
    assert 'gh issue create' in workflow
    assert 'gh pr create' in workflow
    assert 'gh pr merge' not in workflow
    assert 'SETUP.md' in workflow
    assert 'git push\n' not in workflow


def test_bootstrap_requires_reviewed_activation_after_seed_pr() -> None:
    """Initial PR creation cannot silently activate or bypass merge protection."""
    workflow = BOOTSTRAP_WORKFLOW.read_text(encoding='utf-8')
    assert '--github-only' not in workflow
    assert 'gh pr merge' not in workflow
    assert 'SETUP.md' in workflow
    assert 'GITHUB_STEP_SUMMARY' in workflow
    assert 'before merge' in workflow


def test_bootstrap_job_has_timeout() -> None:
    workflow = BOOTSTRAP_WORKFLOW.read_text(encoding='utf-8')

    assert 'timeout-minutes: 30' in workflow


def test_bootstrap_serializes_concurrent_runs() -> None:
    workflow = BOOTSTRAP_WORKFLOW.read_text(encoding='utf-8')

    assert 'concurrency:' in workflow
    assert 'group: ${{ github.workflow }}' in workflow
    # A bootstrap run may be mid rename-and-merge; cancelling it would leave a
    # half-applied specialization. Queued runs must wait, then no-op. Anything
    # other than an explicit false would re-open the two-parallel-renames race.
    assert 'cancel-in-progress: false' in workflow
    assert 'cancel-in-progress: true' not in workflow


def test_bootstrap_pr_is_a_valid_slice_shape() -> None:
    workflow = BOOTSTRAP_WORKFLOW.read_text(encoding='utf-8')

    assert 'gh label create slice' in workflow
    assert 'print(\'\\n\\n## Surfaces\\n- `**`\\n\\n## Out of Scope\\n- (none)\\n\')' in workflow
    assert 'printf \'Closes #%s\\n\' "$issue_number" > bootstrap_pr.md' in workflow


def test_initial_specialization_uses_bootstrap_modes() -> None:
    """The one-shot probe must test a fact that is actually one-shot.

    It used to be `base == "<the template's own name>" and head == repo`,
    which is permanently true *in* the template -- so the version gate exited
    0 before running and both ratchets sat in bootstrap mode on every PR here.
    Comparing base to head asks the question the probe wanted: does this PR
    rename the project? False on every ordinary PR anywhere, true exactly
    once in a derived repository.
    """
    source_template = 'new' '-repository-template'
    for workflow in (
        TYPING_WORKFLOW,
        VERSION_WORKFLOW,
        FAIL_LOUD_WORKFLOW,
    ):
        text = workflow.read_text(encoding='utf-8')
        # All three conditions. The original probe was `base == <seed> and
        # head == repo`, permanently true in the template. Dropping the seed
        # test entirely fixed that but made any rename a bypass, so the probe
        # now needs the base to still be the seed, the name to change, and the
        # repository not to be the template -- true exactly once, in a derived
        # repository's bootstrap PR.
        assert f'base == "{source_template}"' in text, workflow.name
        assert 'base != head' in text, workflow.name
        assert f'repo != "{source_template}"' in text, workflow.name

    ruleset = RULESET_WORKFLOW.read_text(encoding='utf-8')
    assert 'governance/ruleset_gate.py' in ruleset
    assert 'if [ -z' in ruleset and 'RULESET_ID' in ruleset
    assert 'exit 0' not in ruleset


def test_lint_workflow_has_no_template_package_root() -> None:
    workflow = LINT_WORKFLOW.read_text(encoding='utf-8')

    assert 'new_repository_template' not in workflow
    assert 'steps.package.outputs.package_root' in workflow


def test_ruleset_lookup_ignores_organization_rulesets() -> None:
    script = BOOTSTRAP_SCRIPT.read_text(encoding='utf-8')

    assert "item.get('source_type') == 'Repository'" in script


def test_bootstrap_rewrite_leaves_workflow_files_static() -> None:
    script = BOOTSTRAP_SCRIPT.read_text(encoding='utf-8')

    assert "rel_path.startswith('.github/workflows/')" in script
    assert 'changed += _write_workflows(package_name)' not in script
    for dead_name in (
        '_lint_workflow',
        '_honesty_workflow',
        '_typing_workflow',
        '_deploy_workflow',
        '_bootstrap_workflow',
        '_write_workflows',
    ):
        assert f'def {dead_name}' not in script
