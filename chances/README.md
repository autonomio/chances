# Chances package

`chances/` owns seeded scientific generation, observable output validation,
and verifiable archival bundles. The installed entry point is
[the package manual](docs/README.md); the repository's
[documentation hub](../docs/README.md) routes research tasks and maintenance.

## Owned boundary

The package resolves declared specifications, snapshots supported sources,
creates local random generators, executes registered operations, checks results,
and retains provenance for verification and conditional replay.
Scientific method selection, missing-data handling, downstream inference,
author authentication, and physical-entropy attestation are outside this boundary.

## Public entry points

```python
from chances import ChancesError, Generated, catalog, generate, inspect, replay, verify

assert all(callable(name) for name in (catalog, generate, inspect, replay, verify))
```

[The Python API](../docs/Reference/README.md) owns callable signatures and returns.
[Specifications and receipts](../docs/Reference/Specifications-and-Receipts.md) owns the protocol, evidence,
source identity, limits, and replay envelope. The CLI entry point is
`python -m chances`, also installed as `chances`.
Deprecated compatibility exports are described in [migration](../docs/Guides/Migration.md).

## Dependencies and source orientation

NumPy supplies arrays and engines; SciPy supplies registered distribution and
QMC implementations. Both are required runtime dependencies, declared in the
project manifest. No optional runtime extra or remote entropy provider is used.
The documentation site is separate contributor tooling, not an execution dependency.

| File | Responsibility |
| --- | --- |
| `__init__.py` | Public exports and package version. |
| `_api.py` | Protocol resolution, source identity, receipts, archival and replay. |
| `_random.py` | Seed/stream derivation and owned generator state. |
| `_operations.py`, `_distributions.py` | Explicit operation and distribution registry. |
| `_checks.py` | Observable output and structural validation. |
| `_errors.py` | Structured failure type. |
| `__main__.py` | JSON command-line surface. |
| `legacy.py` | Deprecated historical facade. |
| `docs/` | Installed manual, executable workflow, generated contracts and catalog. |

## Operational caveats

Each core request requires a seed. Never infer a distribution or substitute a
method after failure. Saved sources preserve observation order and typed values;
loading forbids pickle. Output publication requires a new destination and rejects
changed result evidence. Unsigned receipts establish integrity relative to retained
evidence; exact replay requires the recorded implementation and environment.

Installed prose mirrors the maintained repository corpus. Contributors edit its
canonical sources and regenerate the installed copies; the mirrored pages are
not a separate documentation authority.

## Read next

Execute [a reproducible batch](../docs/Guides/README.md), or consult
[the operation catalog](../docs/Reference/Operation-Catalog.md) before selecting
parameters.
