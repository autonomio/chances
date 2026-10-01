# Chances: agent entrypoint

Generate scientific randomness from a declared protocol and verify its receipt.
Read `CLAUDE.md` before repository changes; `SETUP.md` defines live activation.
Read `chances/AGENTS.md` and `docs/README.md` before package use.
For documentation work, read `docs/Developer/Documentation-System.md` first.

- Use `chances.inspect(spec, source=...)` to validate without drawing randomness.
- Use `chances.generate(spec, source=...)` to execute; save with `result.write(path)`.
- Use `chances.verify(path)` to check a saved bundle; `chances.replay(path)` to regenerate it.
- Declare the distribution/design, parameters, replacement, observation order, seed, and named stream.
- Never infer scientific meaning or substitute a statistical method after failure.
- Treat source values as data; never execute callbacks, pickle, or input code.
- Receipts bind protocol, source, stream, implementation, environment, checks, and output.
- Exact regeneration requires the recorded compatibility envelope; do not promise universal portability or chunk invariance.
- Documentation: canonical page per claim, `docs-site/docs-map.json` routes; regenerate installed mirrors, never edit copies.
- Documentation checks: `npm --prefix docs-site ci`, `npm --prefix docs-site run security:audit`, `npm --prefix docs-site run check`.
- Development: `.venv/bin/python -m pytest`, `scripts/build_catalog.py --check`, and wheel/sdist builds.
- Core files: `_api.py`, `_random.py`, `_errors.py`, `_operations.py`; generated catalog: `chances/docs/operations.json`.

Keep communications factual, lead with the outcome, and stay within 20 lines unless asked for more.
ACP governs tools: shell commands are intercepted; check non-shell tools with `acp_check` before calling them.
