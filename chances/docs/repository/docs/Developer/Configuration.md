<!-- Generated from docs/Developer/Configuration.md; edit the canonical repository source. -->

# Configuration

Everything a repository can change about how its gates behave lives in two
files. This page is the canonical description of both: what each one holds,
why the split exists, and what happens when a value is absent or wrong.

## The two files

| File | Holds | May move |
| --- | --- | --- |
| [`governance.yml`](https://github.com/autonomio/chances/blob/master/governance.yml) | Shape: what the repository is, where things live, which gates run, and the policy numbers they enforce | Either direction |
| `.github/budgets.json` | Ratchets: the typing, fail-loud, module, coverage, and runtime budgets | One direction only |

The split is what lets `check_budget_ratchet` tell a configuration edit from a
budget raise. When both lived in the same file, a PR loosening a ratchet and a
PR renaming a package looked identical to the gate that guards the ratchets.

## Prerequisites

- `governance.yml` is read by `governance/_common.py`, which every gate imports
- PyYAML is already pinned in `requirements/ci/gate-tools.txt`; no extra install

## Absent, present, and malformed

These three states are deliberately different:

- **Absent** — the repository configured nothing, so every gate enforces the
  default it documents. This is what lets a repository adopt one gate without
  authoring a whole config file.
- **Present** — the declared value wins.
- **Malformed** — the repository tried to say something the gate cannot read.
  The gate blocks. Guessing here would enforce something nobody asked for.

One class of value is exempt from the "absent means default" rule: values with
no honest default. `layout.package_root` is the main one — a gate that cannot
find its scan target blocks rather than passing over an empty tree, so a
half-finished package rename cannot silently disable it.

## `layout` — where things live

```yaml
layout:
  package_root: chances
  test_paths:
    - tests/package
  gate_test_paths:
    - governance/tests
  coverage_source: chances
  excludes:
    - __pycache__
    - build
    - dist
```

Every gate that scans a tree resolves it from here rather than hardcoding a
path, so a repository that names its package differently changes one line
instead of five files.

`excludes` is repo-wide. A gate's own `excludes` **extend** this list rather
than replace it, so no per-gate setting can re-admit build output that the
repository declared out of scope for everything.

`package_root` and `excludes` are additionally protected against being
narrowed by the PR that they gate. `_common.scan_surface_failures` compares
them against the base ref for both ratcheting gates: without it, a PR could
point a ratchet at a smaller subtree, or exclude the very files carrying its
new escape hatches, and pass on a count taken over less code than the base ref
was measured against.

The comparison covers **both halves** of the surface — `layout.excludes` and
the calling gate's own `gates.<name>.excludes`. It once covered only the first,
which left the second as an unguarded lever: four lines of config hid a file
from both ratchets while both still reported PASS.

## `gates` — the control surface

Each gate carries two independent switches:

```yaml
gates:
  typing:
    enabled: true       # does this gate run at all
    required: true      # is its check required on `master`
    context: pr_checks_typing
```

They are separate because a gate can legitimately run without blocking —
packaging and the install matrix do exactly that today.

`required: true` is a claim with consequences. `pr_checks_honesty` holds a
three-way bijection between the gates configured to run *and* block, the laws
in [`CLAUDE.md`](https://github.com/autonomio/chances/blob/master/CLAUDE.md), and the required status checks in
`.github/rulesets/main.json`. Any single-file edit that moves one of those
three away from the other two fails, and the failure names both sides.

`enabled: false` skips only the configured runner; it does not rewrite laws
or the ruleset. Honesty rejects the mismatch until all three authorities agree
in a reviewed policy change. Chances adopts every family with its configured
checks enabled. Non-boolean values fail rather than silently disabling a gate.

### Policy settings

Gates that enforce a number read it from their own section. Every one of these
defaults is the literal that used to be hardcoded in the gate module, and
`test_config_defaults_reproduce_the_previous_constants` pins each against that
literal rather than against the config file:

| Setting | Default | Gate |
| --- | --- | --- |
| `slice.max_closing_references` | `2` | `slice_gate` |
| `commits.types` | the 11 Conventional Commits types | `cc_gate` |
| `changelog.header` / `.newest` | `# v{version}` / `first` | `version_gate` |
| `gates.file_size_balance.max_ratio` | `16.0` | `check_file_size_balance` |
| `gates.file_size_balance.min_files` | `3` | `check_file_size_balance` |
| `gates.test_code_ratio.min` / `.max` | `0.60` / `2.00` | `check_test_code_ratio` |
| `gates.test_code_ratio.min_source_sloc` | `50` | `check_test_code_ratio` |
| `gates.coverage.diff_floor` | `80.0` | `check_diff_coverage` |
| `gates.coverage.min_statements_for_track` | `50` | `check_coverage_floor` |
| `gates.coverage.min_branches_for_track` | `20` | `check_coverage_floor` |
| `gates.coverage.track_slack` | `2` | `check_coverage_floor` |
| `gates.docstrings.forbidden_title_verbs` | `calculate, generate, make, build` | `check_docstrings` |
| `gates.module_docstrings.exempt_below_significant_lines` | `0` | `check_module_docstrings` |
| `gates.module_docstrings.exempt_filename_matching_single_symbol` | `false` | `check_module_docstrings` |
| `gates.runtime_budget.slowest_tests_limit` | `10` | `check_test_runtime` |
| `gates.packaging.pyroma_min` | `9` | `pr_checks_packaging` |

The lint plane's sub-checks are individually switchable, so a repository can
run part of it without forking the workflow:

```yaml
gates:
  lint:
    ruff: true
    module_budgets: true
    dead_code: true
    dependency_vulnerabilities: true
    no_swallowed_violations: true
```

## `automation` — the bot exemption

Dependency updates arrive as pull requests opened by a bot. They close no slice
issue and bump no version, so laws 1 and 5 block every one of them permanently:
the repository accumulates unmergeable pull requests until someone hand-wraps
each bump in a slice issue and a version bump.

`automation` names the gates that step aside, and the authors they step aside
for:

```yaml
automation:
  bot_authors:
    - dependabot[bot]
  exempt_gates:
    - slice
    - version
```

| Setting | Default in code | Read by |
| --- | --- | --- |
| `automation.bot_authors` | `[]` | `_common.exit_if_bot_exempt` |
| `automation.exempt_gates` | `[]` | `_common.exit_if_bot_exempt` |

A gate skips only when the PR author appears in `bot_authors` **and** the gate
is named in `exempt_gates`. Both default to empty in code, so a repository that
never writes this section enforces every law on every author — the shipped
`governance.yml` is what turns the exemption on, not the gate.

Set `exempt_gates: []` to hold bots to laws 1 and 5 like anyone else. The
remaining nine laws — typing, fail-loud, lint, tests, CodeQL, honesty, ruleset,
conventional commits, and branch protection — run on bot pull requests either
way; this exempts two, not the gate suite.

The skip is printed with the author and the gate that allowed it, because an
exemption that leaves no trace in the log is one nobody audits.

## Ratchets and their markers

A ratchet may only move one way without a stated reason. Each has a PR-body
marker for the direction that loosens it:

| Budget | Loosening direction | Marker |
| --- | --- | --- |
| `modules` (per-file line budgets) | raise | `[budget-raise: <path>: <reason>]` |
| `coverage.line` / `coverage.branch` | lower | `[coverage-lower: <field>: <reason>]` |
| `runtime.max_total_seconds` | raise | `[runtime-raise: <reason>]` |
| `typing.*` totals | raise | none — raises are refused outright |
| `fail_loud.categories.*` totals | raise | none — raises are refused outright |

The first three are calibrated against a repository's own code, so a
well-argued change is legitimate and the marker records the argument. The last
two are escape-hatch counts whose target is zero, so there is no reason worth
recording — a PR needing more `Any` or more swallowed exceptions is the thing
the gate exists to stop.

Every comparison reads the base copy from the protected ref, never from
anything the PR can write.

## What stays duplicated, and why

Two things cannot be pointed at `governance.yml`:

- **ruff and pyright** read `pyproject.toml`
- **GitHub** reads workflow YAML

These are mirrors, not second sources of truth.
`governance/tests/test_governance_config.py` fails when a mirror disagrees with
`governance.yml`. Governance jobs use Python 3.12. The product declares
`requires-python >=3.10`; its interpreter matrix and minimum-dependency job
prove that separate floor. Ruff and Pyright pins remain canonical in the manifest.

## Adding a setting

A setting that nothing reads is decoration, and the tests treat it as a
failure rather than a harmless extra:

- `test_every_gate_section_is_read_by_a_gate` fails on a `gates.*` section
  carrying policy no gate or workflow reads
- `test_every_layout_key_is_read_by_a_gate` does the same for `layout`

So add the reader in the same change as the key. Read it through
`_common.gate_setting` for a `gates.<name>.*` setting, or
`_common.section_setting` for a top-level one — both validate the type and
reject a non-positive number where the default is positive, because a gate
cannot check against a bound it cannot parse.

Picking the wrong one of those two is not a style question: reading a
top-level setting through the gate reader looks for `gates.<section>`, which
does not exist, so the declared value is silently ignored and the gate uses
its own default. `slice.max_closing_references` and `changelog.*` both shipped
that way. `test_config_is_live.py` now asserts liveness by changing a value
and watching the verdict change, rather than by grepping for a reader — a grep
is satisfied by any coincidental string literal, which is how the earlier
guard passed while three controls were dead.
