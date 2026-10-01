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
| Merge | ten required checks and sole `bit-mis` approval; the privileged ruleset audit passed on merged master |
| Dependencies | bound manifest, CI hashes, runtime vulnerability gate and explicit expiring exceptions |
| Documentation dependencies | complete-tree audit blocks every known advisory, including development tools |
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

## OpenSSF evidence

[Best Practices entry 15137](https://www.bestpractices.dev/projects/15137)
is the external badge record. `.bestpractices.json` proposes criterion statuses
and source-linked evidence; it distinguishes maintainer attestations from
measured checks. A proposal or progress badge does not mean the project has
earned Passing or Silver.

The initial Scorecard run `36887139175` measured `6.2/10` against merged master
`ee6ab1725bcc60bff78ad45b561dbb3d0b9632da`. Its findings drove read-only
workflow defaults, lockfile remediation and protocol/receipt fuzzing. Verify
subsequent scores against their recorded commit; old review, CI and contributor
history cannot be rewritten by a workflow change. Required mutation permissions
remain in their individual jobs.

The bounded Atheris campaign lives in `fuzz/` and runs from
`.github/workflows/fuzz.yml` and the required lint gate with hash-locked tooling.
It exercises malformed
JSON, bounded structured protocols, deterministic generation and receipt
mutation. Only declared `ChancesError` failures count as expected rejection;
other exceptions and failed invariants crash the campaign and retain evidence.
Fuzzing increases exercised input coverage; it does not prove every possible
input safe. Issue-parser Hypothesis tests remain in the required governance
suite.

For current workflow findings and their evidence, use the
[Scorecard viewer](https://scorecard.dev/viewer/?uri=github.com/autonomio/chances).
Signed-release and packaging detection require successful publication evidence;
a configured publishing workflow alone cannot establish either.

## Residual risk

The current receipt is unsigned. Exact replay depends on the recorded environment.
External method suitability, corrupted hardware, compromised dependencies and
maintainer-account compromise are outside the receipt integrity guarantee.
Dependency scans describe known advisories at check time; undiscovered issues
remain possible.

## Read next

- [Governance adoption](Governance-Adoption.md)
- [Release policy](Release-Policy.md)
