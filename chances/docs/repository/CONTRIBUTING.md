<!-- Generated from CONTRIBUTING.md; edit the canonical repository source. -->

# Contributing

Read [CLAUDE.md](https://github.com/autonomio/chances/blob/master/CLAUDE.md) and [SETUP.md](https://github.com/autonomio/chances/blob/master/SETUP.md). They define the merge laws
and distinguish local preparation from active GitHub enforcement.

## Local setup

Use Python 3.12 for the governance suite; the scientific package also supports
Python 3.10. Use a virtual environment and the locked CI sets:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements/ci/build-tools.txt
.venv/bin/python -m pip install --require-hashes -r requirements/ci/runtime-env.txt
.venv/bin/python -m pip install --require-hashes -r requirements/ci/dev-env.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m pytest tests/package -q --maxfail=1
.venv/bin/python -m pytest governance/tests -q
```

Run the quality and documentation checks in [developer guidance](docs/Developer/README.md).
Every ordinary PR advances the version and changelog, closes its declared slice,
and preserves seeded behavior unless its declared scientific change requires otherwise.
Dependency bots have only the explicit exemptions in `governance.yml`.

## Review

The canonical reviewer brief is [copilot instructions](https://github.com/autonomio/chances/blob/master/.github/copilot-instructions.md).
Follow the activated PR workflow in the constitution. Local checks establish
local evidence; authoritative CI and live branch protection decide merge readiness.
