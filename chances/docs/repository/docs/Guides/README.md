<!-- Generated from docs/Guides/README.md; edit the canonical repository source. -->

# Retain a reproducible batch

Generate one declared computation, save its evidence, verify the archive, and
regenerate the same array. This guide covers a bounded normal draw with no
external source; source-based operations additionally archive their input.

## Prerequisites

Install the current checkout using the [first-success instructions](../../../README.md#first-successful-computation).
Python 3.10 or later, NumPy, and SciPy are required. Choose a seed, a stable stream
name, and a new destination directory before executing a research protocol.
The example uses a temporary directory and deletes it on completion.

## Execute the protocol

1. Declare the distribution, parameters, seed, and stream.
2. Inspect the resolved shape and postconditions before drawing.
3. Generate and publish the result to a new directory.
4. Verify the retained files; replay them while the recorded environment matches.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import chances

spec = {
    "operation": "normal",
    "parameters": {"size": 16, "loc": 0.0, "scale": 1.0},
    "randomness": {"seed": 42, "stream": "study/replicate-1"},
}
profile = chances.inspect(spec)
assert profile["output"]["shape"] == [16]
assert profile["postconditions"]["finite"] is True

with TemporaryDirectory() as temporary:
    bundle = Path(temporary) / "replicate-1"
    result = chances.generate(spec, output=bundle)
    checked = chances.verify(bundle)
    repeated = chances.replay(bundle)
    assert {path.name for path in bundle.iterdir()} == {
        "data.npy", "recipe.json", "receipt.json"
    }
    assert np.array_equal(result.data, checked.data)
    assert np.array_equal(result.data, repeated.data)
    assert result.receipt == checked.receipt == repeated.receipt
```

## Expected evidence

The draw has shape `(16,)`. The new directory contains the output array,
resolved recipe, and receipt. Verification returns the archived values;
replay returns regenerated values with matching evidence. For a persistent
study, retain that directory alongside its analysis rather than using the
example's temporary destination.

Give each replicate its own declared stream. Reordering unrelated computations
does not advance this computation's local generator. Reusing the same resolved
protocol and source repeats it; changing the shape or splitting the draw into
chunks is a different protocol.

## Failure boundaries

An existing destination is rejected. Missing seeds, unknown parameters, invalid
domains, nonfinite data, resource violations, and changed artifacts raise
`ChancesError`. Replay refuses an incompatible recorded environment.
Use [structured recovery](../Reference/Specifications-and-Receipts.md#recovery) to correct the
declared decision; do not replace the method to bypass an error.

A verified receipt is integrity evidence. It does not establish authorship,
independent samples, or the suitability of a normal model for your study.

## Read next

Use [resampling observations](Resampling.md) for index plans, or the
[specification and receipt reference](../Reference/Specifications-and-Receipts.md) to audit the
complete protocol boundary.
