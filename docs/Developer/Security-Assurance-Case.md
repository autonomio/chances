# Security assurance case

This page states the evidence and limits of Chances security controls.
[SECURITY.md](../../SECURITY.md) owns vulnerability reporting;
[governance adoption](Governance-Adoption.md) distinguishes configured and live controls.

## Prerequisites

Read the scientific [receipt contract](../Reference/Specifications-and-Receipts.md)
and the repository [constitution](../../CLAUDE.md). Verification uses Python 3.12
and GitHub CLI; remote claims require live repository evidence.

## Threat model and security requirements

An attacker may control specification JSON, source arrays, saved bundles,
issue text, or proposed repository changes. Their goals include executing
input code, exhausting resources, changing retained results without detection,
overwriting an existing batch, or introducing an unauthorized release.
An accidental invalid scientific request is subject to the same validation.

Chances must reject unsupported syntax and values, bound declared work,
preserve caller-owned inputs and global RNG state, detect altered bundle
content, refuse incompatible replay, and publish a batch without replacing an
existing destination. It must expose failures rather than select a different
scientific method. These claims assume a trusted Python/runtime installation,
filesystem and reviewed implementation; they do not cover compromised hardware
or an attacker who controls the host process. Resource limits bound declared
arrays and work, not every possible native-library execution time.

The [receipt contract](../Reference/Specifications-and-Receipts.md) owns the
user-visible guarantees and compatibility conditions. An attacker who rewrites
all unsigned bundle content and hashes can create a consistent replacement;
hash verification detects integrity mismatch, not authorship or authenticity.

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

## Secure-design argument

| Principle | Applied control and evidence |
| --- | --- |
| Fail-safe defaults | Invalid fields, seeds, source types and limits fail before generation; replay rejects incompatible evidence. See [protocol validation](../../chances/_api.py) and [stream resolution](../../chances/_random.py). |
| Complete mediation | Public inspection and generation resolve inputs through the shared validator; archive verification checks recorded contracts and content before replay. [API tests](../../tests/package) exercise both accepted and rejected inputs. |
| Least privilege and separation | Library calls need no credentials or network service. Workflow defaults are read-only; credentialed publication follows protected manual approval. [Workflow contract tests](../../governance/tests/test_openssf_workflows.py) prohibit default write permissions. |
| Economy of mechanism | Literal JSON, typed arrays and one protocol route avoid executable input formats. Generation, verification and replay share explicit contracts instead of unrelated shortcuts. |
| Open design | Source, schemas, tests, governance rules and this argument are public. Receipts use published SHA-256 rather than a private cryptographic construction. |
| Least common mechanism | Each declared stream owns a local generator; [randomness implementation](../../chances/_random.py) and package tests enforce independence from global RNG state. |
| Psychological acceptability | Inspection reveals resolved choices before drawing; structured failures identify corrections. [Python API](../Reference/README.md) and [quick start](../../README.md#first-successful-computation) show the same path used by agents. |

## Common-weakness argument

| Weakness class | Countermeasure and limit |
| --- | --- |
| Injection and unsafe deserialization (CWE-94, CWE-502) | No input callbacks, code evaluation or pickle. Array loading uses `allow_pickle=False`; literal JSON and dtype allowlists define accepted data. See [input handling](../../chances/_api.py). |
| Improper validation and resource exhaustion (CWE-20, CWE-400) | Validate domains, finite values, array shape, supported dtype and declared resource limits before drawing; check output contracts afterward. [Scientific tests](../../tests/package) and [protocol fuzzing](../../fuzz/fuzz_protocol.py) exercise malformed and extreme inputs. |
| Race and unintended overwrite (CWE-362, CWE-367) | Build a batch in a temporary sibling and publish without replacing an existing destination. [Publication implementation](../../chances/_publication.py) and package tests cover contention and retained evidence. A hostile host/filesystem remains outside the guarantee. |
| Incorrect security assumptions (CWE-345) | Receipt checks bind content and protocol but explicitly make no signature claim. Replay checks the recorded environment; a successful check does not prove scientific suitability. |
| Vulnerable dependencies and unauthorized changes | Locked tooling, runtime and documentation audits, CodeQL, required reviews and live ruleset checks constrain the supply chain. [Dependency policy](Release-Policy.md) and [governance adoption](Governance-Adoption.md) state activation and historical limits. Unknown vulnerabilities and compromised trusted accounts remain risks. |

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
records the Passing badge earned on 2026-10-01. `.bestpractices.json` retains
criterion statuses and source-linked evidence; it distinguishes maintainer
attestations from measured checks. Silver requires separate evidence. The public assessment still records 13%
completion as of 2026-10-02; that percentage includes unanswered fields and does
not measure the percentage of implemented security controls.

The [roadmap](../Roadmap.md) supplies the next-year planning evidence. Maintenance
continuity still needs verified emergency authority and credentials sufficient
to resume issues, merges and releases within one week. Current release signing
requires a completed, publicly verifiable publication; configured workflows are
not evidence that this has occurred. Reporter-credit history and regression-test
coverage of actual bug fixes require a separate historical audit. Unknown facts
remain unknown in the proposal file until supported.

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
