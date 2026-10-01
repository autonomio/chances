<!-- Generated from docs/Developer/Semantic-Versioning.md; edit the canonical repository source. -->

# Semantic versioning

How to decide the bump, and every surface that must carry the result.

## Prerequisites

- the change's public compatibility impact
- the current version, changelog, and citation metadata

## Version surfaces

| surface | role |
| --- | --- |
| `pyproject.toml` | the canonical version for builds and releases |
| `CHANGELOG.md` | the human-readable history; its newest section becomes the release notes |
| `CITATION.cff` | citation version; release date only after publication |
| `chances.__version__` | installed API version, checked against distribution metadata |
| git tag `v<version>` | the release identity `scripts/create_release.py` derives |

## Rules

- **MAJOR** — an incompatible change to the public API, CLI, schema, or
  package contract
- **MINOR** — a new compatible capability
- **PATCH** — a compatible fix, docs correction, metadata correction, or
  dependency refresh

The version gate enforces a minimum from the PR's Conventional Commits type:
`type!` requires major, `feat` requires minor, everything else at least patch.
A larger bump than the minimum is always allowed.

**Every PR bumps the version and adds a changelog section**, including
docs-only PRs. Only the explicit dependency-bot exemption in `governance.yml` skips this gate. The rule is
deliberately absolute: the alternative is a judgement call on every PR about
whether it "counts", and that judgement is where changelog trails go missing.

## Read next

- [Release Policy](Release-Policy.md)
- [Making a Release](Making-Release.md)
