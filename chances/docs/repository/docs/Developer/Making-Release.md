<!-- Generated from docs/Developer/Making-Release.md; edit the canonical repository source. -->

# Making a release

Create the reviewed release from an exact master commit. This procedure is
manual and governed by [release policy](Release-Policy.md).

## Prerequisites

Activate repository controls in [SETUP.md](https://github.com/autonomio/chances/blob/master/SETUP.md). Merge the reviewed
version and changelog change; verify required CI on its exact SHA. The operator
needs access to approve protected release and publishing environments.

## Sequence

1. Record the reviewed `master` SHA and project version.
2. Dispatch `Approved Release` on `master`, supplying the exact project version;
   the workflow binds the dispatch SHA and rejects a changed remote master.
3. Approve its protected `release` environment after reviewing identity and notes.
4. Confirm the created `v<version>` tag and GitHub release refer to that SHA;
   download the complete source archive and source signature bundle and verify
   them using [release policy](Release-Policy.md#retrieve-and-verify-signatures).
5. Before master advances, dispatch the manual PyPI publishing workflow on master
   with the existing tag. The checked-out tag must equal this dispatch SHA;
   approved source provenance is verified before building.
6. Approve its protected `release` environment for the publication build, then
   approve final upload in `pypi`; verify artifacts, digests and attestations.

Expected output is a GitHub release containing authenticated complete source,
wheel, sdist, and verification bundles, followed by the same wheel and sdist on
PyPI. Verify the downloaded PyPI artifacts against the distribution bundle and
approved SHA; archive those consumer-verification results with the run evidence.
The release script rejects a mismatched branch, SHA, remote master or dirty tree
before mutation. An existing tag is not authorization to overwrite it.

## Failures

Missing enablement variables, environment approval, organization `PYPI_API_TOKEN`
or ruleset controls must be resolved before relying on the workflow. Follow the burned-version
recovery rule in [release policy](Release-Policy.md) after partial uploads.

## Read next

- [Release policy](Release-Policy.md)
- [Packaging](Packaging.md)
