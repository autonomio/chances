# Chances

[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/15137/badge)](https://www.bestpractices.dev/projects/15137)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/autonomio/chances/badge)](https://scorecard.dev/viewer/?uri=github.com/autonomio/chances)

Scientific randomness from a declared protocol, with verifiable arrays and execution receipts.

Chances owns generation, validation, archival integrity, and conditional exact replay.
Researchers own the choice of distribution, resampling unit, experimental design,
and interpretation. Core execution requires a seed and uses local generators;
it does not contact an entropy service or change Python or NumPy global RNGs.

The catalog covers 19 operations and 132 distribution families, including
multivariate, empirical, and mixture sampling. Operations also cover whole-row
selection, permutations, bootstrap, stratified splits, balanced allocation,
antithetic pairs, and randomized or quasi Monte Carlo designs.

## First successful computation

This checkout contains the 2.0 API. From its root, use Python 3.10 or later:

```bash
python -m pip install .
```

Installation supplies NumPy and SciPy; no optional runtime extras are required.

```python
import numpy as np
import chances

spec = {
    "version": 1,
    "operation": "normal",
    "parameters": {"size": 100, "loc": 0.0, "scale": 1.0},
    "randomness": {"seed": 42, "stream": "experiment/replicate-1"},
}
profile = chances.inspect(spec)
first = chances.generate(spec)
second = chances.generate(spec)
assert profile["output"]["shape"] == [100]
assert first.data.shape == (100,)
assert np.array_equal(first.data, second.data)
assert first.receipt == second.receipt
```

`inspect` validates and describes without drawing randomness. `generate` returns
`data`, a NumPy array, and `receipt`, JSON evidence. A stream name identifies one
computation; declare different names for distinct replicates. See the
[specification contract](docs/Reference/Specifications-and-Receipts.md) for defaults and stream semantics.

## Retain the evidence

`result.write(directory)` publishes `data.npy`, `recipe.json`, and `receipt.json`
to a new directory. A supplied source also produces `source.npy`.
`verify(directory)` validates the archive; `replay(directory)` regenerates it
and compares its output and evidence. The
[reproducible batch guide](docs/Guides/README.md) executes the complete workflow.

Receipts bind the resolved protocol, source, stream, engine state, implementation,
environment, output identity, and observable mathematical checks. Exact replay
requires the recorded compatibility envelope; there is no cross-version,
cross-platform, or changed-chunk-size equality promise. Unsigned receipts establish
integrity relative to retained evidence, not authorship or scientific suitability.
The [receipt reference](docs/Reference/Specifications-and-Receipts.md) defines these boundaries.

## Choose the next task

| Job | Start here |
| --- | --- |
| Save, verify, and repeat a computation | [Reproducible batch](docs/Guides/README.md) |
| Resample aligned observations or partition strata | [Resampling](docs/Guides/Resampling.md) |
| Retain point designs or treatment allocations | [Experimental design](docs/Guides/Experimental-Design.md) |
| Select a distribution and its parameters | [Operation catalog](docs/Reference/Operation-Catalog.md) |
| Integrate Python or an agent | [Python API](docs/Reference/README.md) |
| Run JSON commands | [Command line](docs/Reference/Command-Line.md) |
| Replace a historical method | [Migration](docs/Guides/Migration.md) |
| Navigate the whole manual | [Documentation hub](docs/README.md) |

Installed agents start at `Path(chances.__file__).parent / "AGENTS.md"`;
the installed manual and catalogs live beside it under `docs/`.
Structured `ChancesError` fields support recovery without substituting a method.

## Contribute, support, and cite

Use [developer setup and validation](docs/Developer/README.md) before proposing
changes. Report defects through [Autonomio Chances issues](https://github.com/autonomio/chances/issues);
include a minimal protocol, package versions, and the structured error.
For a security report, describe the affected interface without publishing private
source data, secrets, or an exploitable artifact in a public issue.

A reproducible research citation should identify Chances, its version, and the
retained protocol and receipt. Use [CITATION.cff](CITATION.cff) for software citation metadata; no DOI is supplied.
Chances is distributed under the [MIT license](LICENSE).
