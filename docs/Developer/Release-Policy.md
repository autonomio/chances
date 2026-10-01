# Release policy

This page owns publication controls. [Making a release](Making-Release.md) owns
the operator sequence. Protected environments are active; the proposed workflows
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

Successful protected publication uploads wheel and sdist, creates GitHub
build-provenance attestations, and records their SHA-256 digests in its job summary.
It creates no SBOM or offline provenance bundle. Verify a workflow-produced artifact:

```bash
gh attestation verify <artifact> --repo autonomio/chances
sha256sum <artifact>
```

## Failure and recovery

A missing control or identity mismatch blocks publication. Inspect the failed
step before retrying. If any artifact reached PyPI, advance the version before
a full publication retry; do not delete and recreate tags or overwrite artifacts.

## Read next

- [Making a release](Making-Release.md)
- [Packaging](Packaging.md)
