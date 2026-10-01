<!-- Generated from THIRD_PARTY.md; edit the canonical repository source. -->

# Third-party notices

Chances uses NumPy and SciPy for its declared scientific engines. Their dependency
bounds are canonical in `pyproject.toml`; CI resolves through hash-pinned sets in
`requirements/ci/`. The docs site uses `docs-site/package.json` and its npm lock.

The adopted scaffold is pinned in [governance adoption](docs/Developer/Governance-Adoption.md).
Its MIT notice is retained in `governance/LICENSE`, `docs-site/LICENSE` and the installed manuals.
The original Chances copyright remains in `LICENSE`.

Before release, review changed dependency licenses, run the runtime dependency
audit and docs-site audit, and retain exact findings. The docs audit blocks high
findings in ordinary production roots and critical findings in the inherited
Docusaurus/search-only subtree; known findings and the acceptance boundary are
explained in [documentation adoption](docs/Developer/Documentation-Adoption.md).
Passing that severity policy does not mean zero known advisories.
