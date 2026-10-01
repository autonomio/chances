# Security Policy

## Supported Versions

Chances 2.0 is under development on this branch. Historical 0.1 releases do
not acquire the new checks retroactively. Report issues against an exact version
or commit; maintainers decide remediation and release timing.

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
