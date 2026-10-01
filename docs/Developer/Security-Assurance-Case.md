# Security assurance case

This page states the evidence and limits of Chances security controls.
[SECURITY.md](../../SECURITY.md) owns vulnerability reporting;
[governance adoption](Governance-Adoption.md) distinguishes configured and live controls.

## Prerequisites

Read the scientific [receipt contract](../Reference/Specifications-and-Receipts.md)
and the repository [constitution](../../CLAUDE.md). Verification uses Python 3.12
and GitHub CLI; remote claims require live repository evidence.

## Trust boundaries

| Boundary | Evidence and limit |
| --- | --- |
| Scientific specification and source | strict literal JSON/array validation, finite values, bounded resources; no pickle or callbacks |
| Receipt bundle | content hashes, protocol checks, owned stream and environment evidence; unsigned integrity, not authenticity |
| Issue and PR text | parser property tests and slice contracts; untrusted text never grants tool authorization |
| Merge | ten configured required checks and protected review snapshot; live activation must be verified |
| Dependencies | bound manifest, CI hashes, runtime vulnerability gate and explicit expiring exceptions |
| Documentation dependencies | audit severity policy in documentation adoption, including inherited Docusaurus findings |
| Actions | SHA-pinned actions, limited permissions, untrusted PR code separated from credentialed mutation |
| Publication | exact master identity, protected manual environments, isolated organization PyPI API token, and GitHub build attestations after successful runs |

## Mechanical proof

The honesty suite binds configuration, laws and required-check snapshot. Mutation
tests assert that removed controls fail. The ruleset gate compares live protection
and the privileged post-merge audit additionally inspects bypass actors.
Ruff enforces code shape; Pyright and fail-loud patterns cannot grow beyond their
measured adoption baseline. Baseline debt remains visible, not silently erased.
Coverage, module size, file balance, test/code ratio, changed-line coverage and
runtime budgets measure distinct constraints; passing one does not prove the others.

Scientific tests cover declared supports, structure, global RNG isolation, source
preservation, receipt tampering and replay. They do not prove every distribution
law from a finite array or choose a scientifically suitable method for a researcher.

## Verification

```bash
python -m pytest governance/tests -q
python -m pytest tests/package -q
gh api repos/autonomio/chances/rulesets
gh attestation verify <artifact> --repo autonomio/chances
```

Local tests prove the candidate checkout. GitHub CI, repository settings and
artifact attestations require separate evidence after publication and activation.

## Residual risk

The current receipt is unsigned. Exact replay depends on the recorded environment.
External method suitability, corrupted hardware, compromised dependencies and
maintainer-account compromise are outside the receipt integrity guarantee.
Known documentation-toolchain advisories remain subject to the declared policy.

## Read next

- [Governance adoption](Governance-Adoption.md)
- [Release policy](Release-Policy.md)
