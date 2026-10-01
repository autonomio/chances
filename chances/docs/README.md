<!-- Generated from README.md; edit the canonical repository source. -->

<div align="center">
  <br />
  <a href="https://github.com/autonomio"><img src="https://avatars.githubusercontent.com/u/28189776?v=4" alt="Autonomio" width="150" height="150" /></a>
  <br />
</div>
<br />
<div align="center"><b>Chances turns declared random computations into checked arrays and repeatable research evidence.</b></div>

<div align="center">
  <a href="#chances">Chances</a> •
  <a href="#what-chances-is-not">Scope</a> •
  <a href="#capabilities">Capabilities</a> •
  <a href="#first-successful-computation">First Computation</a> •
  <a href="#choose-the-next-task">Learn More</a>
</div>
<br />
<div align="center">
  <a href="https://www.bestpractices.dev/projects/15137"><img src="https://www.bestpractices.dev/projects/15137/badge" alt="OpenSSF Best Practices" /></a>
  <a href="https://scorecard.dev/viewer/?uri=github.com/autonomio/chances"><img src="https://api.scorecard.dev/projects/github.com/autonomio/chances/badge" alt="OpenSSF Scorecard" /></a>
  <a href="https://pypi.org/project/chances/"><img src="https://img.shields.io/pypi/v/chances?label=pypi" alt="PyPI version" /></a>
  <a href="repository/docs/README.md"><img src="https://img.shields.io/badge/docs-manual-blue" alt="Chances documentation" /></a>
  <a href="https://github.com/autonomio/chances/actions/workflows/ci-push.yml"><img src="https://github.com/autonomio/chances/actions/workflows/ci-push.yml/badge.svg?branch=master&amp;event=push" alt="Master tests and builds" /></a>
</div>

<hr />

<a id="chances"></a>

# Chances — Scientific randomness

*Scientific randomness from a declared protocol, with verifiable arrays and execution receipts.*

Chances unifies distributions, resampling, allocation, and point designs through
one seeded protocol. Declare the scientific decision, inspect it before drawing,
and retain the result with the evidence needed to verify and repeat it.

## What Chances Is Not

Chances owns generation, validation, archival integrity, and conditional exact replay.
Researchers own the choice of distribution, resampling unit, experimental design,
and interpretation. Chances does not infer those decisions or certify scientific
suitability. It is not a cryptographic random generator or a physical entropy service.
Core execution requires a seed, uses local generators, and leaves Python and NumPy
global random state unchanged.

## Capabilities

The catalog covers **19 operations and 132 distribution families**.

| Research task | Supported capability |
| --- | --- |
| Draw from a scientific model | Univariate and multivariate distributions, empirical samples, and mixtures |
| Resample observations | Whole-row selection, permutations, bootstrap, and stratified splits |
| Plan a study or simulation | Balanced allocation, antithetic pairs, and randomized or quasi Monte Carlo designs |
| Declare independent computations | Explicit seeds and named streams with isolated generators |
| Audit and repeat a result | Validation before drawing, checked arrays, saved receipts, verification, and conditional exact replay |

Use the [operation catalog](repository/docs/Reference/Operation-Catalog.md) to select a family,
its parameters, and its preconditions.

## First successful computation

This README describes the **2.0 API in this repository**. Historical 0.1 releases
on PyPI use a different interface. Start from the current source checkout:

```bash
git clone https://github.com/autonomio/chances.git
cd chances
python -m pip install .
```

Use Python 3.10 or later. Installation supplies NumPy and SciPy; no optional
runtime extras are required. Choose a new output directory for the example;
existing destinations are rejected.

```python
from pathlib import Path
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

bundle = Path("first-batch")
first.write(bundle)
checked = chances.verify(bundle)
repeated = chances.replay(bundle)
assert np.array_equal(first.data, checked.data)
assert np.array_equal(first.data, repeated.data)
assert first.receipt == checked.receipt == repeated.receipt
assert {path.name for path in bundle.iterdir()} == {
    "data.npy", "recipe.json", "receipt.json"
}
print(first.data.shape)
print(bundle.resolve())
```

Expected result: `(100,)` and the absolute path of the retained `first-batch`
directory. The array and receipt match across generation, verification, and
replay in this environment. The example keeps those files for inspection.

`inspect` validates and describes without drawing randomness. `generate` returns
`data`, a NumPy array, and `receipt`, JSON evidence. A stream name identifies one
computation; declare different names for distinct replicates. See the
[specification contract](repository/docs/Reference/Specifications-and-Receipts.md) for defaults and stream semantics.

## Retain the evidence

| File | Retained evidence |
| --- | --- |
| `data.npy` | Generated array |
| `recipe.json` | Resolved scientific protocol |
| `receipt.json` | Source, stream, engine state, implementation, environment, output identity, and mathematical checks |
| `source.npy`, when supplied | Input observations in their declared order |

The same bundle can be inspected from a shell or an agent through JSON commands:

```bash
python -m chances inspect first-batch/recipe.json
python -m chances verify first-batch
python -m chances replay first-batch
```

The [reproducible batch guide](repository/docs/Guides/README.md) covers the full archival
workflow; the [command-line reference](repository/docs/Reference/Command-Line.md) defines
arguments, JSON output, and structured failures.

## Risk Boundary

Exact replay requires the recorded compatibility envelope. It does not promise
equality across package versions, platforms, or changed chunk sizes. Unsigned
receipts establish integrity relative to retained evidence; they do not establish
authorship, independent samples, or the suitability of a statistical model.
The [receipt reference](repository/docs/Reference/Specifications-and-Receipts.md) defines
these boundaries and recovery from changed or incompatible evidence.

## Choose the next task

| Job | Start here |
| --- | --- |
| Save, verify, and repeat a computation | [Reproducible batch](repository/docs/Guides/README.md) |
| Resample aligned observations or partition strata | [Resampling](repository/docs/Guides/Resampling.md) |
| Retain point designs or treatment allocations | [Experimental design](repository/docs/Guides/Experimental-Design.md) |
| Select a distribution and its parameters | [Operation catalog](repository/docs/Reference/Operation-Catalog.md) |
| Integrate Python or an agent | [Python API](repository/docs/Reference/README.md) |
| Run JSON commands | [Command line](repository/docs/Reference/Command-Line.md) |
| Replace a historical method | [Migration](repository/docs/Guides/Migration.md) |
| Navigate the whole manual | [Documentation hub](repository/docs/README.md) |

Installed agents start at `Path(chances.__file__).parent / "AGENTS.md"`;
the installed manual and catalogs live beside it under `docs/`.
Structured `ChancesError` fields support recovery without substituting a method.

<a id="contribute-support-and-cite"></a>

## Contributing

Start with [CONTRIBUTING.md](repository/CONTRIBUTING.md) and
[developer setup and validation](repository/docs/Developer/README.md). Propose work through
[Autonomio Chances issues](https://github.com/autonomio/chances/issues).

## Support

Use [SUPPORT.md](repository/SUPPORT.md) for bug reports, feature requests, and usage questions.
Include a minimal protocol, Chances and Python versions, operating system, and
the structured error. Use a small shareable fixture when a report needs source data.

## Vulnerabilities

Report suspected vulnerabilities privately through
[GitHub Security Advisories](https://github.com/autonomio/chances/security/advisories/new).
Use [SECURITY.md](repository/SECURITY.md) for supported versions, response policy, and artifact
verification. Do not report vulnerabilities through public issues.

## Citations

Use [CITATION.cff](https://github.com/autonomio/chances/blob/master/CITATION.cff) for software citation metadata. A reproducible
research citation should identify Chances, its version, and the retained protocol
and receipt. No DOI is supplied.

## License

[MIT License](https://github.com/autonomio/chances/blob/master/LICENSE).
