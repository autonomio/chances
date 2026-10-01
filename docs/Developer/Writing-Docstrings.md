# Writing docstrings

This page is the docstring contract. Three of its rules are mechanical and
enforced by `governance/check_docstrings.py`; the rest are the stance the
operator applies at review, and no gate can check them.

## Prerequisites

- none for reading
- to run the gate: `python governance/check_docstrings.py`

## What the gate enforces

Three deterministic rules, on every function and method docstring in the
package. They are deliberately domain-neutral — a template cannot know what
your data means, so it checks only what is true regardless.

| rule | violation message |
| --- | --- |
| The title verb is not `calculate`, `generate`, `make`, or `build` | `title verb 'build' is forbidden` |
| No description states a default value | `description states a default value '(default: ...)'; drop it` |
| A note marker is written `NOTE:`, never `Note:` or `note:` | `note marker 'Note:' must be written 'NOTE:'` |

**Why those four verbs.** They describe the machine's activity rather than the
caller's result. `Calculate the ratio` tells a reader the function does
arithmetic, which they assumed; `Return the ratio of X to Y` tells them what
they get back. Open with a verb that says what the function *delivers*:
`Compute`, `Return`, `Parse`, `Validate`, `Resolve`, `Extract`.

**Why defaults are banned from descriptions.** The default is in the
signature. Restating it creates a second place to be wrong, and it will be:
signatures change and prose does not.

**Why `NOTE:` is uppercase.** So it is greppable. A marker you cannot find
mechanically is a comment, not a marker.

Module-level docstrings are a separate gate,
`governance/check_module_docstrings.py`: one line, required on every non-empty
module unless [`governance.yml`](../../governance.yml) exempts it. `ruff` D415 already
requires a title ending in a period, so this gate does not re-check it.

## What the gate cannot check

The stance in [CLAUDE.md](../../CLAUDE.md) rejects docstrings that restate the
signature, narrate the line, or describe a parameter that "might be useful
someday". None of that is mechanizable — a docstring saying
`"""Return the user id."""` on `def user_id() -> int` is perfectly formed and
says nothing.

The test is whether the docstring tells a reader something the signature does
not: a constraint, a failure mode, a unit, a boundary. If it does not, delete
it rather than pad it.

## Read next

- [Documentation System](Documentation-System.md)
- [Developer home](README.md)
