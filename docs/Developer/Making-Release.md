# Making a release

A reviewed version change releases automatically after master verification.
[Release policy](Release-Policy.md) owns the authorization and artifact contract.

## Prerequisites

Activate branch-restricted environments and organization `PYPI_API_TOKEN` using
[SETUP.md](../../SETUP.md). Keep `RELEASE_ENABLED=true` and
`PYPI_PUBLISH_ENABLED=true`. Neither environment requires an additional reviewer.

## Sequence

1. Bump the project version and newest changelog section in a PR; pass all ten
   required checks and obtain the required bit-mis merge review.
2. Merge to master. Successful `Verify and build` starts `Approved Release`.
   The request must identify that exact master SHA and an unreleased version.
3. The release signs complete source, verifies its identity, creates the immutable
   tag and GitHub release, and attaches the source archive and signature bundle.
4. Successful `Approved Release` starts `Publish Package to PyPI`. It checks the
   exact source and builds, audits, signs, and publishes immutable distribution
   assets before handing the same wheel and sdist to the isolated upload job.
5. Verify downloaded GitHub and PyPI artifacts against their public bundles and
   the exact source SHA using [release policy](Release-Policy.md#retrieve-and-verify-signatures).

Expected output is a GitHub release containing authenticated complete source,
wheel, sdist, and verification bundles, followed by the same wheel and sdist on
PyPI. No second review or manual release dispatch is part of the normal path.
An existing version tag on an older commit skips automatic publication. Eligibility
uses immutable tags, so version bumps earlier in a multi-commit merge are recognized.

## Recovery and failures

Manual dispatch remains available on master for an exact version or existing tag
when recovering a failed run. The same source, signature, and immutability checks
apply. Missing enablement, credentials, failed verification, or an advanced master
blocks publication visibly. Never replace published bytes or reuse a PyPI version
after a partial upload; follow [release policy](Release-Policy.md#failure-and-recovery).

## Read next

- [Release policy](Release-Policy.md)
- [Packaging](Packaging.md)
