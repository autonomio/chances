# Activate Chances governance

This runbook activates the checked-in governance package for `autonomio/chances`,
whose default branch is `master`. Local adoption alone activates no remote controls.
The existing product must never be run through template seed specialization.

## Prerequisites

Use an administrator with explicit authority to change repository settings.
Review the exact proposed `.github/rulesets/main.json`, workflows, constitution
and measured budgets before activation. Preserve the previous settings for rollback.

## Access and review

Verify `zero-bang` and every named CODEOWNER have repository write access; remove
invalid ownership entries through a reviewed policy change. GitHub enforces
one non-author approval, last-push approval and required ownership review.
The project requests `zero-bang`; GitHub does not constrain all approvals to
one named login. Initial master has no CODEOWNERS: record explicit operator
approval for this adoption; ownership enforcement starts after that file is merged. Copilot review is automatically requested, not a substitute
for required human approval.

## Apply and verify protection

1. Review the candidate on its existing branch. Pass local policy and mutation
   preflight; confirm the ten configured contexts and GitHub Actions integration.
   The live-ruleset check cannot pass before steps 2 and 3.
2. Apply `.github/rulesets/main.json` as `Protect-Master`; it must target
   `refs/heads/master`, be active, contain no bypass actors and enforce the declared checks.
3. Set repository variable `RULESET_ID` to its returned numeric identifier.
4. Provision `RULESET_AUDIT_TOKEN` for this repository only, initially with
   Administration read access and an actor authorized to inspect ruleset bypasses.
   Prove that its live response includes `bypass_actors` and passes the privileged
   audit; a permission label alone does not prove visibility. Keep the token out
   of untrusted PR execution.
5. Publish the candidate and run all ten required CI contexts on its exact SHA.
   Run the ruleset audit and compare its complete live result with the snapshot.
   Before merge, prove scoped-token visibility locally; the new post-merge audit
   workflow becomes dispatchable only after it exists on master.
   Check direct-push, force-push, deletion, up-to-date and review controls.

Missing `RULESET_ID`, denied access or drift fails visibly. Do not treat a skipped
or unavailable platform check as a pass. The label-copy workflow needs a declared
source; `LABEL_TEMPLATE_REPOSITORY` defaults to this existing repository and
does not imply another Autonomio template exists. `REPO_BOOTSTRAP_TOKEN` is
for seed bootstrap only; do not provision it to rewrite Chances.

## Release controls

Create protected `release` and `pypi` environments with required reviewers,
prevent self-review, disallow administrator bypass where supported, and restrict
deployment branches to `master`; publish dispatch stays on master while
checking out its validated existing release tag.
Verify reviewers, self-review prevention, and the exact master branch policy
through the environment API before enabling workflows. Verify administrator
bypass is disabled through the GitHub environment UI or a supported API response;
ordinary REST update documentation does not declare that input parameter.

Set `RELEASE_ENABLED=true` only after the release environment and live master
ruleset pass inspection. Set `PYPI_PUBLISH_ENABLED=true` only after configuring
the PyPI trusted publisher for this repository, `pr_publish_pypi.yml`, and `pypi`.
Retire the unused `PYPI_USERNAME` and `PYPI_PASSWORD` secrets after confirming
no retained workflow uses them. Manual dispatch still requires environment approval.

Follow [making a release](docs/Developer/Making-Release.md); publish no artifact
until the exact merged SHA, tag, version, checks and approval are verified.

## Verification and rollback

```bash
gh api repos/autonomio/chances/rulesets
gh variable list --repo autonomio/chances
gh api repos/autonomio/chances/environments
python -m pytest governance/tests -q
```

Record live ruleset ID, settings, commit SHA and CI runs in the activation PR.
If protection or publishing fails, disable enablement variables, retain artifacts
and logs, and reconcile policy in review. Never overwrite published versions or
use bypass actors to conceal a failing required check.
