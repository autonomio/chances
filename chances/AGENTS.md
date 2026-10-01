# Chances: agent entrypoint

Generate scientific randomness from an explicit JSON specification.
Use `chances.inspect(spec, source=...)` to validate without drawing.
Use `chances.generate(spec, source=...)` to return `data` and `receipt`.
Use `verify(directory)` to validate an archive; `replay(directory)` to regenerate.
Package root is `Path(chances.__file__).parent`; paths below are relative to it.

- Start and installation: `docs/README.md`.
- Specification grammar, receipts, replay, recovery: `docs/recipes.md`.
- Operation names, parameters, preconditions: `docs/operations.json`.
- Historical methods and scientific behavior changes: `docs/migration.md`.
- Executable saved research workflow: `docs/research_batch.py`.

Declare the seed, distribution/design, parameters, shape, and named stream.
Use a distinct stream for each independent replicate; preserve its specification.
Never select a different scientific method, coerce invalid data, or add entropy.
On failure, inspect `ChancesError.code` and `.details`, correct the decision, rerun.
Replay needs the recorded input, package/runtime versions, and environment.
Receipts establish integrity, not authenticity or scientific appropriateness.
