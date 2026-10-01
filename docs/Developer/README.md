# Develop Chances

Maintain the scientific protocol and its evidence together. Runtime behavior is
authoritative; documentation describes the current implementation. This page
owns contributor setup and validation.

## Prerequisites

Use Python 3.12 for governance; the scientific product supports Python 3.10 or later. Documentation additionally needs Node.js 20 or later,
npm, and Playwright Chromium. NumPy and SciPy versions are declared in
[the project manifest](../../pyproject.toml).

## Install and verify

From a repository checkout:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install '.[dev]'
python -m pytest tests/package -q
python -m pytest governance/tests -q
python scripts/build_catalog.py --check
python test_script.py
python -m build
```

The tests assert scientific contracts, source preservation, global RNG isolation,
receipt integrity, structured failures, and exact replay. The example publishes
a bounded batch to a temporary directory, verifies it, and replays it. The build
produces a wheel and source distribution in `dist/`. CI installs both outside
the checkout and executes the shipped workflow.

## Documentation ownership

Author each claim once in its [canonical section](../README.md).
[The system contract](Documentation-System.md) defines page roles, appearance,
and acceptance. [Documentation adoption](Documentation-Adoption.md) records
the documentation baseline, adaptations and deployment boundary.
[Governance adoption](Governance-Adoption.md) records the complete enforcement rollout.

Update the route map when adding or moving a maintained page. Regenerate the
installed manual and catalogs with `python scripts/build_catalog.py`; generated
copies are not independent prose. Read
[the documentation toolchain](../../docs-site/README.md) for site commands.

## Governance and maintenance

- [Constitution](../../CLAUDE.md) and [activation](../../SETUP.md)
- [Configuration](Configuration.md), [docstring rules](Writing-Docstrings.md) and [technical debt](Technical-Debt.md)
- [Packaging](Packaging.md), [versioning](Semantic-Versioning.md) and [release policy](Release-Policy.md)
- [Making a release](Making-Release.md) and [security assurance](Security-Assurance-Case.md)
- [Contribution](../../CONTRIBUTING.md), [governance](../../GOVERNANCE.md), [maintainers](../../MAINTAINERS.md), [security reporting](../../SECURITY.md) and [support](../../SUPPORT.md)

## Failure and review boundary

A failed contract, changed example, stale catalog, broken link, or incompatible
replay is a defect to resolve. Do not select another statistical method to make
a test pass. Runtime contract changes need their own stated scientific effect;
documentation work alone does not authorize one.

## Read next

Review [the documentation system contract](Documentation-System.md) before
editing public pages, or [the package boundary](../../chances/README.md) before
changing implementation.
