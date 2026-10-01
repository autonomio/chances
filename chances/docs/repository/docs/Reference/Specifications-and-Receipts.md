<!-- Generated from docs/Reference/Specifications-and-Receipts.md; edit the canonical repository source. -->

# Specifications, receipts, and replay

This reference owns the versioned scientific specification, source identity,
random-stream contract, resource limits, receipt evidence, and replay boundary.
The [Python API](README.md) owns callable signatures;
the [catalog reference](Operation-Catalog.md) owns registry navigation.

Python protocol trees accept native JSON literals (and native tuples as arrays).
Custom container, scalar and path subclasses are rejected before normalization
and artifact access;
this boundary prevents their input callbacks from running. Receipt comparison
preserves JSON literal types: Boolean values cannot impersonate integer dimensions,
counts or seeds, even when the bundle is consistently rehashed. Native NumPy source
scalars are converted only after their exact scalar class is recognized.

## Public surface

Use `from chances import inspect, generate, verify, replay`.
`inspect(spec, *, source=None)` resolves and validates without drawing;
`generate(spec, *, source=None, output=None)` returns `Generated(data, receipt)`.
`verify(directory)` checks an archived result; `replay(directory, *, output=None)`
regenerates after checking compatibility. Writing is an explicit side effect:
`result.write(directory)` and the `output` argument publish a new bundle.
NumPy and SciPy are required dependencies; no optional runtime extras are needed.

## One declared computation

```json
{
  "version": 1,
  "operation": "normal",
  "parameters": {"size": 100, "loc": 0.0, "scale": 1.0},
  "randomness": {
    "seed": 42,
    "stream": "experiment/replicate-1",
    "engine": "pcg64dxsm"
  }
}
```

| Field | Requirement and default |
| --- | --- |
| `version` | Integer `1`; defaults to `1`. |
| `operation` | Required registered operation name. |
| `parameters` | Object containing that operation's named parameters; defaults to `{}` before resolution. |
| `randomness` | Object containing a required seed and optional stream and engine. |
| `limits` | Optional positive integer resource budgets; defaults below. |

Specifications are Python dictionaries or regular local UTF-8 JSON files.
Documents must fit 1 MiB and contain finite JSON values. Duplicate JSON keys,
unknown fields, and unknown parameters are errors. Version 1 is the only
supported specification version. Resolved defaults are retained in the receipt.
Consult the generated `operations.json` before choosing parameters.

`inspect` reports an `output` estimate containing dtype, shape, value count, and
bytes. Its `postconditions` describes exact shape/dtype, finite values, support,
and any dependence or stratification. Review these before allocating a batch.
Scientific labels and interpretation belong to the researcher's protocol.

Where accepted, `size` is a nonnegative integer or list of nonnegative axis
lengths. `size=[]` requests a scalar; zero-length axes request empty output.
Multivariate event dimensions follow the requested draw shape. Complete outputs
support at most 16 axes. The selected family's parameters define mathematical
units; bytes in the inspector are storage units for the resulting dtype.

## Randomness

Every core specification requires `randomness.seed`: an integer in `[0, 2**256)`.
Booleans are rejected. `stream` defaults to `"default"`; provide a nonempty name
of at most 512 UTF-8 bytes after Unicode NFC normalization. `engine` defaults to
`"pcg64dxsm"`. The supported engines are `pcg64dxsm`, `pcg64`, `philox`, `sfc64`,
and `mt19937`: scientific pseudo-random generators, not cryptographic services.

The versioned `sha256-seed-stream-v1` derivation hashes the seed and normalized
stream into a NumPy SeedSequence. Each call creates its own generator; no shared
generator or global RNG is advanced. Evidence records complete bit-generator
state and SeedSequence entropy, spawn key, pool size, and child-spawn count
before and after execution. SciPy QMC can spawn a child without advancing the
parent bit-generator; the SeedSequence record retains that transition.

The same seed and stream deliberately reuse a stream. Repeating a resolved
specification and source repeats its output in the recorded environment;
changing shape or distribution changes stream consumption. Do not assume calls
sharing a stream are independent. Declare distinct stream names for replicates
or stages and retain them. Scheduling unrelated calls does not advance this
call's generator. Changed chunks, split draws, or changed algorithms do not have
an output-equivalence promise.

## Sources and observation order

Source-capable operations accept a native NumPy array, rectangular literal
sequence, or regular local `.npy` file. Boolean, integer, float, Unicode, and
fixed-width byte-string arrays are supported with at most 16 axes. Object,
complex, structured, nonfinite, masked, and custom ndarray subclass inputs are
rejected. Literal sequences must preserve value types and integer precision;
mixed string/numeric identifiers and lossy numeric coercions are rejected.
File loading forbids pickle, symbolic links, and special files.

Resolve missingness and metadata at the data-preparation boundary. Source row
order is part of identity; reordered values are different inputs. Declare
replacement and sample size when relevant. Pass aligned observations together
or apply a shared observation-index plan. Input arrays are not mutated.
A source snapshot is hashed and saved as `source.npy`, so replay uses the
archived input rather than a potentially changed external file.

Choice and permutation select whole rows. Bootstrap returns observation indices;
apply them consistently across aligned variables. Cluster bootstrap requires
equal-sized clusters for rectangular output. Circular block bootstrap preserves
within-block order and wraps at the source boundary. No mode silently falls
back to ordinary bootstrap.

Stratified sampling declares a label per observation and count per stratum.
`stratified_sample` returns indices in label-major order; replacement defaults
to false. `stratified_split` uses a count matrix with strata as rows and partitions
as columns; indices are partition-major and sliced using column totals.
Explicit `labels` fixes stratum order; otherwise first occurrence establishes it.
A source establishes observation count, while both operations still return indices.
See [resampling workflows](../Guides/Resampling.md) for complete examples.

## Resource limits

| Budget | Default | Unit |
| --- | --- | --- |
| `max_values` | `10000000` | Array values. |
| `max_bytes` | `268435456` | Array storage bytes. |
| `max_work` | `100000000` | Estimated operation and validation work units. |

Overrides must be positive integers below `2**63`. Limits bound declared output
size and estimated work before large allocations. Work includes verification
costs such as uniqueness sorting and matrix checks. A limit failure requires
revising the request or declaring a justified budget; output is never silently
shrunk. Estimates are guardrails, not wall-clock or process peak-memory guarantees
for third-party numerical routines. Protocol and receipt JSON each fit 1 MiB.

## Designs and distributions

Pseudo-random draws and quasi Monte Carlo designs solve different problems.
Sobol and Halton produce unit-hypercube points; Latin hypercube controls marginal
strata. These are not interchangeable independent draws. Sobol requires a
power-of-two count to preserve its balance contract. The catalog states each
construction's count, dimension, scrambling, and support rules.
Poisson disk uses bounded sequential dart throwing: exact count and declared
separation, or `SAMPLING_EXHAUSTED`. It does not promise maximal packing or
uniformity across all feasible configurations.

The `distribution` operation accepts a registered family name, named parameters,
and `size`. Univariate continuous families expose `loc` and `scale`; univariate
discrete families expose `loc`. Multivariate families have separate vector/matrix
contracts. Parameter meanings follow the selected registered SciPy family.
Domain and support validation are explicit. Nonfinite draws fail. Uniform
operations use their declared endpoint-rounding mapping to retain interval
support; no undeclared transform or hidden retry conceals a failed check.

A mixture is `distribution="mixture"` with explicit scalar registered SciPy
components and weights. Components cannot be nested mixtures or vector events.
The float output preserves draw assignment order. Inspect resolved components
and probabilities before execution.

`antithetic` creates an even number of normal or uniform point rows. The first
half and reflected second half form dependent pairs, subject to floating rounding.
Uniform endpoints follow the catalogued open-interval mapping. Any variance
reduction depends on the integrand; independent sampling is not its contract.

## Save, verify, replay

This bounded example publishes and checks a temporary bundle, then deletes it.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import chances

spec = {
    "operation": "normal",
    "parameters": {"size": 8},
    "randomness": {"seed": 42, "stream": "reference/archive"},
}
with TemporaryDirectory() as temporary:
    root = Path(temporary)
    result = chances.generate(spec, output=root / "batch")
    checked = chances.verify(root / "batch")
    repeated = chances.replay(root / "batch", output=root / "replayed")
    assert np.array_equal(result.data, checked.data)
    assert np.array_equal(result.data, repeated.data)
    assert result.receipt == checked.receipt == repeated.receipt
```

A bundle contains `data.npy`, `recipe.json`, and `receipt.json`; supplied sources
add `source.npy`. Arrays are saved without pickle. Recipe JSON uses sorted keys,
UTF-8, compact separators, and finite values. Receipt identity has no execution
timestamp.

| Receipt field | Evidence |
| --- | --- |
| `receipt_version` | Receipt schema version, currently `1`. |
| `versions`, `environment` | Package/runtime and execution compatibility envelope. |
| `spec`, `spec_sha256` | Resolved specification and its hash. |
| `source` | Source identity, or `null`. |
| `randomness` | Seed, normalized stream, engine, derivation, complete before/after state. |
| `contract` | Resolved observable mathematical postconditions. |
| `checks` | Seven required successful validation flags. |
| `output` | Output identity. |
| `receipt_sha256` | Hash of all receipt fields except itself. |

Array identity contains `dtype`, `shape`, `values`, `bytes`, and `sha256`.
Hashes bind dtype, shape, and C-order bytes under `chances-array-v1`; source strides
and NPY headers do not change identity. The generated `contracts.json` enumerates
exact schema fields, engine names, defaults, and hashing rules.

The seven flags are `finite`, `supported_dtype`, `resource_limits`, `shape`,
`dtype`, `declared_support`, and `structural_constraints`, each `true`.
Applicable checks cover whole source rows, replacement/permutation multiplicities,
allocation and stratum counts, within-cluster/block order, antithetic reflection,
marginal design strata, Sudoku coarse cells, and Poisson disk separation.
The `contract` is checked against the saved protocol. These are observable facts,
not proof of a sampling law from one array.

`write` detects changed data, source, or evidence, stages and validates files,
then publishes a new directory. Native atomic exclusion rejects existing outputs,
including a destination created during publication. Linux requires
`renameat2(RENAME_NOREPLACE)`, macOS requires `renamex_np(RENAME_EXCL)`,
and Windows uses its exclusive `os.rename` behavior. Unsupported platforms,
filesystems, or unavailable native calls fail with `OUTPUT_FAILED`; there is no
overwriting fallback. Failed validation publishes no result. Changed outputs
need a new declared computation and evidence.

`verify` validates archive identity, resolved protocol, postconditions, and complete
state records; it returns archived values without regeneration. `replay` verifies,
checks compatibility, regenerates from the saved request/source, and compares the
complete result evidence. The recorded envelope includes Chances, NumPy, SciPy,
Python version/build, platform, machine/processor, byte order, CPU count,
numerical build configurations, and selected thread environment variables.
Replay refuses a mismatch.

Exact equality is conditional on that envelope. Floating implementations can
change across libraries, builds, and CPU/platforms. Seed and engine alone do not
establish universal portability. Retain the actual artifact when its values matter.
Verification can establish archival integrity without asserting current replayability.

Receipts are unsigned. SHA-256 detects changed data relative to retained evidence;
a writer replacing arrays and evidence can make a different consistent artifact.
Receipts do not attest authorship, prove independence, or establish scientific
appropriateness.

## Recovery

`ChancesError` exposes `code`, `details`, and `to_dict()`. The
[command line](Command-Line.md) reports protocol errors as
JSON with unsuccessful exit status; malformed command syntax has its own usage response.

| Failure | Required decision |
| --- | --- |
| Missing or invalid seed | Declare the intended integer; never invent entropy. |
| Unknown operation, engine, argument | Follow the installed catalog. |
| Invalid domain or design | Correct the scientific specification. |
| Incompatible source or counts | Preserve intended values and observation identity. |
| Resource limit | Inspect costs and revise the batch or justified budget. |
| Changed artifact or evidence | Retain the archive for investigation; regenerate into a new destination from the original protocol/source. |
| Replay incompatibility | Use the recorded environment, or verify archived values without claiming regenerated equivalence. |
| Existing or busy destination | Choose a new destination or wait for its publisher. |

Never silently select another distribution, change replacement, reorder
observations, weaken checks, or discard inconvenient values.

## Read next

Execute [a reproducible batch](../Guides/README.md), or select the
[resampling workflow](../Guides/Resampling.md) appropriate to your declared
observation unit.
