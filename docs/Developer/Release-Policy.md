# Release policy

This page owns publication controls. [Making a release](Making-Release.md) owns
the operator sequence. Protected environments are active; source-signing changes
become available after merge. Historical 0.1 releases do not gain their protections
or attestations retroactively.

## Prerequisites

Activate the live ruleset and protected environments through [SETUP.md](../../SETUP.md).
Use a reviewed, merged `master` commit with the exact version and changelog.

## Version and approval

Use [semantic versioning](Semantic-Versioning.md). A tagged or uploaded version
is burned; never reuse it. Partial PyPI uploads require a new version.

| Control | Mechanism |
| --- | --- |
| Merge to master | ten required checks and protected review rules |
| Release creation | manual dispatch, `RELEASE_ENABLED=true`, protected `release` environment |
| Release identity | exact master SHA, clean worktree, tag from project version |
| Notes | reviewed changelog section and mechanically appended traceability |
| Publish enablement | `PYPI_PUBLISH_ENABLED=true` and manual publish dispatch |
| PyPI upload | organization `PYPI_API_TOKEN`, authenticated as `__token__`, from protected `pypi` environment |
| Filename availability | pre-build PyPI check rejects already served versions |
| Consumer artifacts | content audit, metadata validation, deterministic build evidence |

Environment protection must be configured remotely; naming an environment in
YAML does not itself provide an approval gate. The isolated upload job receives
`PYPI_API_TOKEN` only after approval and rejects missing or incorrectly prefixed tokens.
Old organization username/password secrets remain unchanged for other repositories.
Token authentication does not generate PyPI digital attestations; GitHub build
provenance remains independently attested. No authentication fallback is allowed.

## Release deliverables

The approved-release workflow archives every tracked repository file, including
scientific code, tests, governance, and documentation. It rejects archive exclusions
and submodules rather than silently omitting source. The archive is signed through
GitHub build-provenance attestation before tag or release creation. The annotated
Git tag itself is unsigned; artifact signatures do not sign a Git tag.

The publishing workflow requires the release-tag checkout to equal its `master`
dispatch SHA. It reconstructs the complete source archive and verifies both byte
identity and the release workflow's provenance before building. Successful
publication attaches wheel, sdist, and their signature bundle to the GitHub release
before handing those same distributions to the separately approved PyPI job.
Existing release assets are retained only when their bytes match; replacements
fail. PyPI uploads remain protected separately and can still fail after GitHub
assets exist. No successful signed 2.0 publication is claimed until its workflow
and consumer verification complete. No SBOM is produced.

### Retrieve and verify signatures

Use the current [GitHub CLI](https://cli.github.com/manual/gh_attestation_verify).
The release assets contain `chances-<version>-source.tar.gz`, wheel and sdist,
`source-<run-id>-<attempt>.sigstore.json`, and
`distributions-<run-id>-<attempt>.sigstore.json`. Retrieve them from the specific
[GitHub release](https://github.com/autonomio/chances/releases).
Each bundle includes the signing certificate and transparency-log evidence.
GitHub public-repository attestations use the Sigstore public-good trust service;
there is no project private signing key to distribute. GitHub CLI validates the
certificate chain against its Sigstore trust roots and enforces the workflow,
repository, GitHub OIDC issuer, source ref, and exact source commit specified below.
See [GitHub's attestation trust model](https://docs.github.com/en/actions/concepts/security/artifact-attestations).
A local bundle avoids attestation API lookup; obtaining CLI trust roots can still
require network access, so this is not a claim of fully offline verification.

Set `ARTIFACT` to the downloaded file, `BUNDLE` to its corresponding downloaded
signature bundle, and `APPROVED_SHA` to the reviewed full commit SHA identified by
the release tag. For complete source, use:

```bash
gh attestation verify "$ARTIFACT" --bundle "$BUNDLE" \
  --repo autonomio/chances --source-digest "$APPROVED_SHA" \
  --source-ref refs/heads/master --deny-self-hosted-runners \
  --signer-workflow autonomio/chances/.github/workflows/pr_post_release.yml
```

For each wheel or sdist, use the same verification command with signer workflow
`autonomio/chances/.github/workflows/pr_publish_pypi.yml` and its distribution
bundle. The archive and distributions must verify against the same approved SHA.
Without `--bundle`, the CLI retrieves attestations through GitHub's API. Digest-only
comparison cannot authenticate an artifact; keep the full identity constraints.

## Failure and recovery

A missing control or identity mismatch blocks publication. Inspect the failed
step before retrying. An interrupted GitHub asset upload can resume with identical
bytes and a new run-specific signature bundle; differing asset bytes fail. If master
advances beyond the release commit before publication dispatch, prepare a reviewed
new version instead of disabling the exact-source guard. If any artifact reached PyPI, advance the version before
a full publication retry; do not delete and recreate tags or overwrite artifacts.

## Read next

- [Making a release](Making-Release.md)
- [Packaging](Packaging.md)
