# Resample observations and partition strata

Retain a shared observation-index plan so aligned measurements use the same
resampled rows. This guide demonstrates paired bootstrap and a complete
stratified split; it does not select a resampling unit or estimate uncertainty.

## Prerequisites

Install Chances using the [first-success instructions](../../README.md#first-successful-computation).
Prepare finite rectangular observations in their intended row order.
Declare whether the unit is an observation, cluster, or ordered block before
choosing a bootstrap mode. The examples use small in-memory fixtures;
the first archives its plan and input in a temporary directory.

## Retain a paired bootstrap plan

1. Put aligned measurements in the same observation rows.
2. Declare the number of resamples and observations in each resample.
3. Generate indices, then apply that one plan to every aligned measurement.
4. Save and verify the plan before interpreting an analysis built from it.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
import chances

observations = np.arange(12, dtype=float).reshape(6, 2)
spec = {
    "operation": "bootstrap",
    "parameters": {"resamples": 4, "sample_size": 6, "mode": "paired"},
    "randomness": {"seed": 42, "stream": "study/paired-bootstrap"},
}
profile = chances.inspect(spec, source=observations)
assert profile["output"]["shape"] == [4, 6]

with TemporaryDirectory() as temporary:
    bundle = Path(temporary) / "bootstrap-plan"
    result = chances.generate(spec, source=observations, output=bundle)
    samples = observations[result.data]
    assert samples.shape == (4, 6, 2)
    assert np.all(samples[..., 1] - samples[..., 0] == 1)
    assert (bundle / "source.npy").is_file()
    assert chances.verify(bundle).receipt == result.receipt
    assert np.array_equal(chances.replay(bundle).data, result.data)
```

Bootstrap returns indices with shape `(resamples, sample_size)`, even when a
source is supplied. The derived `samples` array belongs to the separate analysis;
the saved receipt covers the index plan and source, not every later calculation.

## Split a population while retaining strata

1. Declare one group label for each observation.
2. Set a count matrix with strata as rows and partitions as columns.
3. Generate the flat index plan and slice it using the column totals.

```python
import numpy as np
import chances

groups = np.array(["a", "a", "a", "b", "b", "b"])
result = chances.generate({
    "operation": "stratified_split",
    "parameters": {
        "groups": groups.tolist(),
        "labels": ["a", "b"],
        "counts": [[2, 1], [2, 1]],
    },
    "randomness": {"seed": 42, "stream": "study/partition"},
})
first, second = result.data[:4], result.data[4:]
assert np.array_equal(np.sort(result.data), np.arange(6))
assert np.count_nonzero(groups[first] == "a") == 2
assert np.count_nonzero(groups[first] == "b") == 2
assert np.count_nonzero(groups[second] == "a") == 1
assert np.count_nonzero(groups[second] == "b") == 1
```

The split covers every observation exactly once. Its output is partition-major;
explicit `labels` fixes the count-matrix row order. Each partition is randomized.
`stratified_sample` instead returns a requested subset in stratum-major order.

## Failure boundaries

Unequal cluster sizes are rejected by cluster bootstrap because output must be
rectangular. Circular block bootstrap preserves order inside sampled blocks and
wraps at the source boundary. These modes are not silently substituted.
Stratified split row totals must cover each stratum exactly; sampling without
replacement cannot exceed a stratum's population. Source row order and its
values are part of the retained identity. Missingness and identifiers need an
explicit data-preparation decision before generation.

## Read next

Check mode parameters and ordering in the [operation catalog](../Reference/Operation-Catalog.md),
then use the [receipt reference](../Reference/Specifications-and-Receipts.md) to retain and audit
the declared protocol.
