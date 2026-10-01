# Packaging

This page owns the consumer artifact boundary and its proof. Hatch is the
build backend declared in `pyproject.toml`; the enforcement checkout is separate.

## Prerequisites

Use the locked packaging tools in `requirements/ci/packaging-tools.txt`. Builds
need the declared scientific dependencies and generated manuals to be current.

## Artifact policy

The wheel contains `chances/`, portable manuals and package metadata. It excludes
tests and repository governance. The source distribution also retains canonical
docs, docs-site source and npm lock, scientific tests, catalog and benchmark
scripts, and public metadata. It excludes governance code, GitHub workflows,
CI locks, node_modules, generated site output and browser reports.

`pyproject.toml` selects files; `scripts/package_audit.py` verifies required and
forbidden paths. The sdist is a source-inspection and rebuild artifact, not the
full enforcement repository. To inspect merge controls, use the canonical Git checkout.

An extracted sdist with `PKG-INFO` and no Git metadata may check its shipped
manuals using the checkout-validated repository-link inventory in `sources.json`.
The source pages, profile and route map must match their recorded digests;
`contracts.json` binds the complete inventory digest. Edited or inconsistent
artifacts fail and require regeneration in a Git checkout, where missing link
targets always fail. These unsigned freshness bindings do not authenticate an
artifact against coordinated replacement. Excluded enforcement files remain
canonical GitHub links; installed manuals do not require them locally.

## Dependency policy

Runtime dependencies carry both bounds, or an exact pin. `requirements/constraints.txt`
is the human-readable CI resolver envelope; `requirements/ci/*.txt` are the
compiled hash-pinned installations. Ruff and Pyright exact pins live in the manifest.

## Reproducibility

Build identical source twice with the same declared build environment and epoch:

```bash
SOURCE_DATE_EPOCH=1704067200 python -m build --no-isolation --outdir /tmp/chances-build-one
SOURCE_DATE_EPOCH=1704067200 python -m build --no-isolation --outdir /tmp/chances-build-two
python scripts/package_audit.py /tmp/chances-build-one
```

The packaging workflow compares SHA-256 digests of both wheel and sdist. Hatch
normalizes archive metadata; no replacement setuptools backend is introduced.
Byte identity is evidence for that environment, not a promise across build-tool versions.
Core metadata is explicitly 2.4 for compatibility with the locked validators.

## Required proof

The packaging workflow builds twice, compares every artifact, audits content and
bounds, validates metadata with Twine and Pyroma, and checks the VCS manifest.
The product matrix installs artifacts outside the source checkout, checks imports
and version metadata, and executes the shipped receipt workflow.

Packaging is advisory in the inherited merge ruleset; protected publication
runs artifact validation before upload. See [release policy](Release-Policy.md).

## Read next

- [Release policy](Release-Policy.md)
- [Developer home](README.md)
