<!-- Generated from docs/Guides/Experimental-Design.md; edit the canonical repository source. -->

# Retain point designs and group allocations

Generate an explicit design, retain its evidence, and verify its observable
constraints. This guide covers a scrambled Sobol point design and a balanced
group allocation. The research protocol chooses which construction is suitable.

## Prerequisites

Install Chances using the [first-success instructions](../../../README.md#first-successful-computation).
Declare the dimension and point count for a point design, or labels and group
counts for an allocation. The examples are bounded; the point-design archive
uses a temporary directory and is deleted on completion.

## Retain a Sobol design

1. Declare a power-of-two point count, dimension, and scrambling choice.
2. Inspect the array shape and postconditions.
3. Generate, archive, verify, and replay the design.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import chances

spec = {
    "operation": "sobol",
    "parameters": {"n": 16, "d": 2, "scramble": True},
    "randomness": {"seed": 42, "stream": "study/sobol-design"},
}
profile = chances.inspect(spec)
assert profile["output"]["shape"] == [16, 2]

with TemporaryDirectory() as temporary:
    bundle = Path(temporary) / "sobol-design"
    result = chances.generate(spec, output=bundle)
    assert np.all((result.data >= 0) & (result.data < 1))
    assert chances.verify(bundle).receipt == result.receipt
    assert np.array_equal(chances.replay(bundle).data, result.data)
```

The result contains 16 two-dimensional points in the unit hypercube. Sobol is a
quasi Monte Carlo construction, not a collection of independent uniform draws.
Any transformation of these points into physical parameter units belongs to
your analysis and needs its own retained definition.

## Allocate exact group counts

1. Declare group sizes and their labels.
2. Generate a randomized label vector in observation order.
3. Retain it before assigning observations or evaluating outcomes.

```python
import numpy as np
import chances

result = chances.generate({
    "operation": "balanced_allocation",
    "parameters": {"counts": [6, 6], "labels": ["control", "treated"]},
    "randomness": {"seed": 42, "stream": "study/allocation"},
})
assert result.data.shape == (12,)
assert np.count_nonzero(result.data == "control") == 6
assert np.count_nonzero(result.data == "treated") == 6
```

The output assigns six labels to each group. It does not attach subject IDs or
justify the allocation protocol; preserve your observation order separately.
Save this vector with `result.write(new_directory)` when using it in a study.

## Failure boundaries

Sobol rejects non-power-of-two counts. Each design has its own sample-count,
dimension, and scrambling constraints; Halton, Latin hypercube, Sudoku, Korobov,
and Poisson disk are not interchangeable substitutes. Poisson disk uses bounded
sequential dart throwing and either returns the exact requested count with its
separation constraint or raises `SAMPLING_EXHAUSTED`.

Observable support, strata, and structural checks do not establish a design's
suitability for an integrand or an experiment. Antithetic draws deliberately
create dependent pairs; they do not promise universal variance reduction.

## Read next

Use the [operation catalog](../Reference/Operation-Catalog.md) for each construction's
parameters and the [batch guide](README.md) to retain a persistent result.
