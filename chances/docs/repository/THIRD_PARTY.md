<!-- Generated from THIRD_PARTY.md; edit the canonical repository source. -->

# Third-party notices

Chances uses NumPy and SciPy for its declared scientific engines. Their dependency
bounds are canonical in `pyproject.toml`; CI resolves through hash-pinned sets in
`requirements/ci/`. The docs site uses `docs-site/package.json` and its npm lock.

The adopted scaffold is pinned in [governance adoption](docs/Developer/Governance-Adoption.md).
Its MIT notice is retained in `governance/LICENSE`, `docs-site/LICENSE` and the installed manuals.
The original Chances copyright remains in `LICENSE`.

Before release, review changed dependency licenses, run the runtime dependency
audit and docs-site audit, and retain exact findings. The docs audit checks the
complete locked tree, including development tools, and blocks every known
advisory. [Documentation adoption](docs/Developer/Documentation-Adoption.md)
defines the acceptance boundary; scans describe known advisories at check time.

## Documentation backports

The documentation lock uses locally patched braces 3.0.3 (MIT) and
http-cache-semantics 4.2.0 (BSD-2-Clause). Upstream licenses, registry provenance,
file hashes, and the exact repair boundary are retained under
`docs-site/vendor/`. These forks repair the reported depth-exhaustion and
security-blocked cache-reuse defects; they are not upstream releases.
The scientific wheel does not include them.
