# Security Policy

## Supported Versions

The maintained source is the 2.0 series on `master`; its release artifacts are
published only through the protected workflows. Historical 0.1 releases do not
acquire the new checks retroactively. Report issues against an exact version
or commit; maintainers identify affected versions during triage.

## Reporting a Vulnerability

Report suspected vulnerabilities privately through GitHub Security Advisories:

- [Private vulnerability report](https://github.com/autonomio/chances/security/advisories/new)

Do not open a public issue for a vulnerability.

Include:

- affected version or commit
- reproduction steps
- expected impact
- any logs or proof artifacts that are safe to share privately

Reporters are credited in the release notes and `CHANGELOG.md` entry of the fix unless they request otherwise.

## Response and disclosure

Maintainers aim to acknowledge private reports within 14 days. They reproduce
the report, assess impact and affected versions, and coordinate a fix and
disclosure with the reporter. Critical vulnerabilities receive priority.
Confirmed medium-or-higher vulnerabilities that become public must be fixed
and released within 60 days, unless a documented mitigation or evidence shows
the reported issue does not apply.

Release notes must identify every publicly known vulnerability fixed by the
release, including its CVE or other public identifier when assigned.
Publish a GitHub security advisory and release notes for confirmed fixes; credit
the reporter unless they opt out. These targets define the response process;
they are not evidence of past response times.

## Verifying Release Artifacts

Release workflows following verified protected-master merges authenticate complete tracked repository
source and built distributions through GitHub provenance attestations. Successful
runs publish the source archive, wheel, sdist, and downloadable Sigstore bundles
on the GitHub release; the separate PyPI job uploads the same distributions.
Historical releases do not acquire these guarantees retroactively, and configured
workflows alone are not evidence of a completed signed release.

Follow the exact source SHA, signer identity, and public trust-root verification
instructions in [Release Policy](docs/Developer/Release-Policy.md#retrieve-and-verify-signatures).
SHA-256 digests alone do not establish authenticity. Report verification mismatches
through the private channel above. Scientific result receipts and annotated Git
tags remain unsigned; release artifact signing does not change their guarantees.
A CycloneDX SBOM is not produced.

## Scope

Security scope covers repository code, the governance gates, packaging, release artifacts, docs-site deployment configuration, and dependency metadata maintained in this repository.
