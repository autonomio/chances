# Chances in one page

Chances turns a declared random computation into a checked NumPy array and a
receipt. It supports scientific distributions, observation-index plans,
allocations, permutations, and point designs through the same seeded protocol.

## Start with the job

| Reader job | Route |
| --- | --- |
| First computation | [Install and generate](../README.md#first-successful-computation) |
| Retain a reproducible batch | [Generate, verify, replay](Guides/README.md) |
| Preserve pairing or strata | [Resample observations](Guides/Resampling.md) |
| Plan points or allocate groups | [Experimental design](Guides/Experimental-Design.md) |
| Build an agent or Python integration | [Python API](Reference/README.md) |
| Find a family and named parameters | [Operation catalog](Reference/Operation-Catalog.md) |
| Use files and JSON commands | [Command line](Reference/Command-Line.md) |
| Migrate old shortcuts | [Migration from 0.1](Guides/Migration.md) |

## From protocol to retained result

1. Declare the scientific operation, parameters, observation order, seed, and
   stream in a [specification](Reference/Specifications-and-Receipts.md).
2. Call [inspect](Reference/README.md) to resolve defaults and review shape,
   dtype, resource estimates, and mathematical postconditions without drawing.
3. Call [generate](Reference/README.md) to execute with an owned local generator.
   The first observable result is an array plus its receipt.
4. [Save a batch](Guides/README.md) to retain the resolved recipe, output, evidence,
   and any supplied source together.
5. [Verify or replay](Reference/Specifications-and-Receipts.md#save-verify-replay) to check the
   archive or regenerate under its recorded environment.
6. Apply the retained array or index plan in your analysis. Chances responsibility
   ends at its declared output contract; inference and scientific suitability
   remain the researcher's responsibility.

## The five sections

| Section | Authority and entry |
| --- | --- |
| Overview | [Product home](../README.md) and [release history](../CHANGELOG.md) |
| Guides | [Reproducible batch](Guides/README.md), [resampling](Guides/Resampling.md), [experimental design](Guides/Experimental-Design.md), [migration](Guides/Migration.md) |
| Reference | [Python API](Reference/README.md), [catalog](Reference/Operation-Catalog.md), [CLI](Reference/Command-Line.md), [specifications and receipts](Reference/Specifications-and-Receipts.md) |
| Developer | [Develop Chances](Developer/README.md), [documentation contract](Developer/Documentation-System.md), [adoption evidence](Developer/Documentation-Adoption.md), [site toolchain](../docs-site/README.md) |
| Packages | [Chances package boundary](../chances/README.md) |

## Product boundary

Chances validates explicit data and parameters, generates with seeded scientific
engines, checks observable output constraints, and archives replay evidence.
It does not infer missing scientific decisions, execute input code, load pickle,
attest physical entropy, or prove statistical laws from a single observed array.
A receipt is unsigned. Regeneration is conditional on the saved compatibility
envelope, described in the [receipt reference](Reference/Specifications-and-Receipts.md).

## Read next

Complete [a reproducible batch](Guides/README.md), then select the
[research workflow](Guides/Resampling.md) or [API surface](Reference/README.md)
your task needs.
