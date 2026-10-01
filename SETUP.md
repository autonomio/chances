# Activate Chances governance

This runbook activates the checked-in governance package for `autonomio/chances`,
whose default branch is `master`. Local adoption alone activates no remote controls.
The existing product must never be run through template seed specialization.

## Prerequisites

Use an administrator with explicit authority to change repository settings.
Review the exact proposed `.github/rulesets/main.json`, workflows, constitution
and measured budgets before activation. Preserve the previous settings for rollback.

## Access and review

Verify `bit-mis` has repository write access. Remove invalid ownership entries
through a reviewed policy change. GitHub enforces
one non-author approval, last-push approval and required ownership review.
The project requires `bit-mis`; sole global CODEOWNER `* @bit-mis` makes
their approval mandatory through GitHub ownership protection. Initial master has
no CODEOWNERS: record explicit operator approval for this adoption; ownership
enforcement starts after that file is merged. Copilot review is automatically
requested, not a substitute for required human approval.

## Apply and verify protection

1. Review the candidate on its existing branch. Pass local policy and mutation
   preflight; confirm the ten configured contexts and GitHub Actions integration.
   The live-ruleset check cannot pass before steps 2 and 3.
2. Apply `.github/rulesets/main.json` as `Protect-Master`; it must target
   `refs/heads/master`, be active, contain no bypass actors and enforce the declared checks.
3. Set repository variable `RULESET_ID` to its returned numeric identifier.
4. Provision the organization-wide `RULESET_AUDIT_TOKEN` using the runbook below.
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

## Organization-wide ruleset audit secret

Create the token while signed in as an Autonomio organization owner whose account
can edit the audited repository rulesets. A token cannot exceed its owner's access;
sharing it as an organization secret does not grant additional repository access.

1. Open personal **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**. Name it `Autonomio ruleset audit`;
   select an expiration within organization policy, for example 90 days, and
   rotate it before expiry.
2. Set **Resource owner** to `autonomio` and **Repository access** to
   **All repositories**. Under repository permissions, set **Administration** to
   **Read-only**; retain the automatically required Metadata read permission and
   grant no other permissions. Generate and copy the token. Owner-created tokens
   are automatically approved; other creators may need approval under organization
   **Settings → Personal access tokens → Pending requests**. Follow
   [GitHub's fine-grained token instructions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token).
3. Open Autonomio **Settings → Secrets and variables → Actions → Secrets →
   New organization secret**. Set **Name** to `RULESET_AUDIT_TOKEN`, paste the
   token as its value, select **Repository access → All repositories**, and
   click **Add secret**. Do not paste the token into chat, source or command
   arguments. Follow [GitHub's organization-secret instructions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets#creating-secrets-for-an-organization).
4. Prove the actual token locally with `governance/privileged_ruleset_audit.py`,
   supplying it securely through `GH_TOKEN`, before relying on the secret. Require
   `PRIVILEGED RULESET AUDIT -- PASS`; a missing `bypass_actors` field fails setup.
   GitHub returns that field only when the requesting actor can edit the ruleset;
   Administration read alone is not proof. Stop if visibility is missing rather
   than silently widening token permissions. See [the ruleset API](https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset).

Each repository needs its own `RULESET_ID` Actions variable and an audit workflow
that runs only on its protected default branch; the secret supplies the credential.
The Chances workflow already reads `secrets.RULESET_AUDIT_TOKEN`. Remove or update
stale same-name repository or environment secrets because they override the
organization value. GitHub Free does not expose organization secrets to private
repositories; use a plan supporting them to cover those repositories. See
[secret precedence](https://docs.github.com/en/actions/reference/security/secrets)
and [organization-secret availability](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets#creating-secrets-for-an-organization).

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
ruleset pass inspection. Set `PYPI_PUBLISH_ENABLED=true` after configuring the
protected `pypi` environment and making organization secret `PYPI_API_TOKEN`
available to this repository. The upload job requires a nonempty PyPI API token
and authenticates as `__token__`; it never substitutes username/password secrets
or OIDC after a failure. The build job never receives the PyPI credential.
Keep organization `PYPI_USERNAME` and `PYPI_PASSWORD` unchanged: other repositories
may still use them. Manual dispatch still requires environment approval.

On 2026-10-01, both environments were verified through the live API: sole required
reviewer `bit-mis` has repository write access, self-review is blocked, administrator
bypass is disabled, and the only deployment branch policy is exact `master`. The proposed workflows become available
after merge; activation does not create a tag or publish a release.

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
