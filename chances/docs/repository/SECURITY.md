<!-- Generated from SECURITY.md; edit the canonical repository source. -->

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

The adopted manual publishing workflow creates GitHub build-provenance
attestations when activated and used. Historical releases have no such guarantee.
For an artifact produced by that workflow, verify with:

```bash
gh attestation verify <artifact> --repo autonomio/chances
```

SHA-256 digests of every built artifact are recorded in the publish run's job summary. The verification contract is documented in [Release Policy](docs/Developer/Release-Policy.md). Report verification mismatches through the private channel above.

A CycloneDX SBOM and an offline `provenance.intoto.jsonl` bundle are **not** produced today; verification is against the attestation API rather than a downloaded bundle.

## Scope

Security scope covers repository code, the governance gates, packaging, release artifacts, docs-site deployment configuration, and dependency metadata maintained in this repository.
