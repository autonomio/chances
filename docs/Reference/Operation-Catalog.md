# Operation catalog

The generated catalog owns operation names, parameters, defaults, source
requirements, constraints, output contracts, and distribution examples. This
page explains how to consult that authority without maintaining a second list.

## Read the public catalog

```python
from chances import catalog

entries = catalog()
assert entries["schema_version"] == "chances.operations.v1"
assert "bootstrap" in entries["operations"]
assert "beta" in entries["distributions"]
```

`catalog()` takes no arguments, returns a dictionary, and consumes no randomness.
`operations` maps names to `parameters`, `source`, `output`, and `constraints`.
`distributions` maps family names to their kind, shape parameters, accepted
parameters, and a bounded `example`. Family-specific entries can describe
additional event shapes or support. Examples contain family parameters;
they are not complete generation specifications.

The same catalog is installed at
`Path(chances.__file__).parent / "docs" / "operations.json"`.
The adjacent generated `contracts.json` records engine, array-identity,
resource-default, and receipt contracts. These files are generated from current
implementation; contributors regenerate them rather than editing them.

## Execute one family example

```python
import numpy as np
import chances

entry = chances.catalog()["distributions"]["beta"]
spec = {
    "operation": "distribution",
    "parameters": {"distribution": "beta", "size": 32, **entry["example"]},
    "randomness": {"seed": 42, "stream": "reference/beta"},
}
profile = chances.inspect(spec)
result = chances.generate(spec)
assert profile["output"]["shape"] == [32]
assert np.all((result.data >= 0) & (result.data <= 1))
```

Here `size` counts draws and the example supplies the beta family's named shape
parameters. Location and scale have the selected family's mathematical units.
Multivariate families declare vector or matrix parameters and append event axes.
The [specification reference](Specifications-and-Receipts.md#designs-and-distributions)
explains those shared conventions and intentional dependence boundaries.

## Constraints and failures

`inspect` validates a catalogued request and reports its resolved postconditions;
it does not draw a preview sample. Unknown names or fields, invalid parameters,
nonfinite output, and resource violations fail explicitly. No unregistered SciPy
object, callback, or arbitrary input code is executed through this surface.

Distribution examples are executable fixtures, not recommendations for a
research model. Choosing another family or design after a failure changes the
scientific protocol. No optional distribution extras are required beyond the
project's NumPy and SciPy dependencies.

## Read next

Use [resampling](../Guides/Resampling.md) or [experimental design](../Guides/Experimental-Design.md)
for complete jobs; use [the Python API](README.md) to integrate a selected entry.
