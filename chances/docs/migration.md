<!-- Generated from docs/Guides/Migration.md; edit the canonical repository source. -->

# Migrate from Chances 0.1

Replace a historical shortcut with a declared scientific operation, seed,
stream, and retained result. Chances 2.0 is a major-version change: historical
outputs and accidental global-RNG behavior are not preserved. This guide covers
interface migration, not evidence that old and new scientific results agree.

## Prerequisites

Install the current checkout through the [first-success instructions](README.md#first-successful-computation).
Recover the old call's intended distribution or design, population, observation
order, replacement policy, and scientific resampling unit before replacing it.
No optional runtime extras are required.

## Review the changed contract

| Historical behavior | Version 2 contract |
| --- | --- |
| Hidden NumPy/Python global RNGs | Required seed, named stream, local generator. |
| Integer index shortcuts for designs | Explicit `n` and `d`; point arrays with documented design guarantees. |
| Print-only smoke checks | Deterministic assertions, catalog checks, archive verification, replay. |
| Quantum or ambient network services | No remote providers in core; explicit unavailable-provider failure. |
| Implicit entropy fallback | No substitute generator for unavailable entropy. |
| Values without provenance | Array plus resolved request, checks, and receipt. |
| Historical module imports | Small public API and installed manual/catalog navigation. |

1. Identify the mathematical intent of the old method.
2. Select the corresponding explicit operation from the
   [catalog](repository/docs/Reference/Operation-Catalog.md).
3. Declare all scientific parameters and a seed/stream; inspect before generating.
4. Verify expected shape and constraints, then
   [retain the new result](repository/docs/Guides/README.md).

## Replace a subset call

For the declared intent “choose ten distinct indices from a population of one
hundred,” use choice without replacement:

```python
import numpy as np
import chances

spec = {
    "version": 1,
    "operation": "choice",
    "parameters": {"n": 100, "size": 10, "replace": False},
    "randomness": {"seed": 42, "stream": "study/subset"},
}
profile = chances.inspect(spec)
result = chances.generate(spec)
assert profile["output"]["shape"] == [10]
assert result.data.shape == (10,)
assert len(set(result.data.tolist())) == 10
assert np.all((result.data >= 0) & (result.data < 100))
```

The result is ten unique valid indices, with a receipt for the new protocol.
It does not claim equality to a version 0.1 draw. Use `permutation` for a complete
ordering; use `normal`, `uniform`, or `integers` for their declared distributions.
Use point-design operations when retaining multidimensional geometry matters.
Bootstrap indices form a shared plan for aligned variables; clusters and ordered
blocks require their own declared modes. Do not infer these decisions from names.

## Legacy facade and failure boundaries

`chances.Randomizer` remains deprecated and is also available through
`chances.legacy`. It uses an owned seed, defaulting to `0` for migration.
Review its outputs as new results. Its design methods return integer lists and
discard multidimensional geometry. Legacy `sobol()` requires a power-of-two
population; `latin_improved()` rejects its quadratic work-budget excess.

Legacy `quantum()` and `ambience()` raise `ENTROPY_PROVIDER_UNAVAILABLE` without
contacting a provider or quietly selecting another source. Explicit
`uniform_crypto()` uses local OS-backed cryptographic randomness; fresh draws
cannot be regenerated from a seed. Core specification operations require seeds
and replay under their recorded compatibility envelope.

The modern API supplies no physical-entropy or quantum attestation system.
Such a study needs a separately chosen, validated, and archived entropy protocol.
Invalid parameters, source types, or domains require a scientific correction;
legacy availability does not authorize a fallback after failure.

## Read next

Use [the specification reference](repository/docs/Reference/Specifications-and-Receipts.md) for source identity, streams, and
receipt semantics, then complete [the saved batch workflow](repository/docs/Guides/README.md).
