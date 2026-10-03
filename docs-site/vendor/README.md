# Documentation security backports

The documentation lock overrides every `braces` and `http-cache-semantics`
consumer with these locally maintained source packages. These are Autonomio
backports, not published upstream fixes. They are excluded from the scientific
wheel and retained in source distributions that include documentation tooling.

| Package | Upstream base | Local version | Repair |
|---|---|---|---|
| braces | 3.0.3 | 3.0.3-autonomio.1 | Bound parser and direct-AST depth to 100; reject cyclic or oversized ASTs before recursive walkers |
| http-cache-semantics | 4.2.0 | 4.2.0-autonomio.1 | Refuse security-blocked cache reuse before considering max-stale or stale-while-revalidate |

`provenance.json` records the original registry URL and integrity, upstream
file digests, and every local file digest. Original MIT and BSD-2-Clause licenses
remain inside their packages. The manifest version changes identify the forks;
removing a registry audit warning is not the proof of repair.

The reported exploit conditions and normal behavior are tested in
`../tests/security-backports.test.mjs`. Tests also prove that every installed
consumer resolves the local implementation. The required documentation gate
runs those tests after a clean locked installation. A registry audit continues
checking the rest of the complete dependency tree, without advisory exceptions.

Upstream reports:

- [braces depth exhaustion](https://github.com/micromatch/braces/issues/70)
- [cache reuse prohibitions](https://github.com/kornelski/http-cache-semantics/issues/56)

Maintain these patches only until reviewed upstream replacements repair the same
regressions. Preserve the exploit tests when removing the local overrides.
