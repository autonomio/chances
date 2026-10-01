# Python API

This reference owns the public execution surface. Scientific parameters and
receipt fields are defined by the [specification reference](Specifications-and-Receipts.md)
and [operation catalog](Operation-Catalog.md).

## Public names

```python
from chances import ChancesError, Generated, catalog, generate, inspect, replay, verify

assert callable(inspect) and callable(generate)
assert callable(verify) and callable(replay) and callable(catalog)
```

| Signature | Returns | Effects |
| --- | --- | --- |
| `inspect(spec, *, source=None)` | Description dictionary | Resolves and validates; snapshots and hashes supplied source; draws no randomness. |
| `generate(spec, *, source=None, output=None)` | `Generated` | Uses a local generator; optional `output` publishes a new bundle. |
| `verify(directory)` | `Generated` | Reads and validates a local bundle; does not regenerate its computation. |
| `replay(directory, *, output=None)` | `Generated` | Verifies compatibility, regenerates, and compares evidence; optional `output` saves a new bundle. |
| `catalog()` | Catalog dictionary | Describes registered operations and distributions; draws no randomness. |
| `result.write(directory)` | `pathlib.Path` | Validates unchanged result/evidence and publishes a new bundle. |
| `ChancesError(code, message, details=None)` | Exception | Exposes `.code`, `.details`, and `.to_dict()`. |

`spec` is a dictionary or local UTF-8 JSON file path. `source` is an accepted
native NumPy array, rectangular literal sequence, or regular `.npy` file path.
`output` and `directory` are paths; publication requires a new directory.
No optional runtime dependencies are required beyond installed NumPy and SciPy.

## Returned fields

`inspect` returns `resolved_spec`, `source` identity or `None`, the `operation`
catalog entry, `output` estimate, `postconditions`, and a `replay` boundary string.
The estimate reports `dtype`, `shape`, `values`, and `bytes`; bytes use the array's
dtype width, not an estimate of process peak memory. Postconditions describe
shape, dtype, finite values, support, and any declared dependence or stratification.

`Generated` exposes `data`, a NumPy array, and `receipt`, a dictionary. Generation
initially returns read-only arrays. The receipt binds the resolved protocol and
observable result checks. Changing values or evidence does not create a valid
new computation; `write` detects changes and rejects publication.

## Minimum computation

```python
import numpy as np
import chances

spec = {
    "operation": "normal",
    "parameters": {"size": 4},
    "randomness": {"seed": 42, "stream": "reference/example"},
}
profile = chances.inspect(spec)
result = chances.generate(spec)
assert profile["output"]["shape"] == [4]
assert profile["output"]["bytes"] == result.data.nbytes
assert result.receipt["spec"] == profile["resolved_spec"]
assert all(result.receipt["checks"].values())
assert np.array_equal(result.data, chances.generate(spec).data)
```

## Errors and edge cases

Unknown fields, missing seeds, invalid domains, unsupported sources, resource
violations, changed evidence, and incompatible replay raise `ChancesError`.
Inspect its structured fields before correcting the declared protocol.
[Recovery](Specifications-and-Receipts.md#recovery) owns the failure response rules.

Scalar and empty draw shapes are supported where the operation permits them;
multivariate event axes extend the draw shape. The complete output has at most
16 axes. Local file loading forbids pickle, symbolic links, and special files.
Resource estimates are guardrails, not timing or peak-memory guarantees.

Deprecated `Randomizer` and `generate_random_alpha` exports remain for migration;
use [the legacy migration guide](../Guides/Migration.md) for their boundaries.

## Read next

Choose parameters through the [operation catalog](Operation-Catalog.md), or
execute the [saved batch workflow](../Guides/README.md).
