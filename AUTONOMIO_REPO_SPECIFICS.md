# Chances repository-specific rules

Appendix to [PR guidance](AUTONOMIO_PR_GUIDELINE.md).

This appendix is scoped to Autonomio/Chances; it makes no claim about other repositories.

- `[repo:authority]` Constitution and active policy: [CLAUDE.md](CLAUDE.md), [governance.yml](governance.yml).
- `[repo:layout]` Source package: `chances/`; scientific tests: `tests/package/`; gate tests: `governance/tests/`.
- `[repo:branch]` Protected base branch: `master`; current adoption branch: `codex/chances-2`.
- `[repo:fixtures]` Scientific random generation and bounded fixtures are the declared product, not fabricated research observations.
- `[repo:randomness]` Preserve seeded outputs and receipt semantics during mechanical refactors.
- `[repo:runtime]` Product Python floor: 3.10; governance runtime: 3.12.
- `[repo:artifacts]` Build backend: Hatch; wheels ship portable manuals, source distributions also retain canonical docs.
- `[repo:activation]` Activation and remote prerequisites: [SETUP.md](SETUP.md).
- `[repo:documentation]` Documentation authority: [documentation system](docs/Developer/Documentation-System.md).
