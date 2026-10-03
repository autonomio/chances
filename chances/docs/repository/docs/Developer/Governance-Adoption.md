<!-- Generated from docs/Developer/Governance-Adoption.md; edit the canonical repository source. -->

# Governance adoption

This page records Chances adoption of the full governance scaffold at pinned
commit `fa7bf92caab5bb8d7f73120d4dc3526fd86c0348`. Organization references and
MIT scaffold notices are adapted to Autonomio under operator authorization.
The original Chances MIT notice remains unchanged.

## Prerequisites and authority

`governance.yml` defines repository shape and policy; `.github/budgets.json`
defines ratchets; [CLAUDE.md](https://github.com/autonomio/chances/blob/master/CLAUDE.md) defines eleven laws.
[SETUP.md](https://github.com/autonomio/chances/blob/master/SETUP.md) owns activation and its verification.

## Scope and adaptations

- All gate families, ten required checks, ruleset snapshot, mutation tests,
  parser property tests, CI locks, review brief, issue templates and release controls are adopted.
- Base branch is `master`; product is `chances`, using Hatch and Python 3.10+.
  Governance runs on Python 3.12.
- The template seed bootstrap is retained as a guarded tool and refuses to
  rename an established Chances checkout.
- Product artifacts retain portable manuals; the sdist also retains canonical
  documentation source for inspection and rebuild. Repository enforcement stays in Git.
- Documentation audit, links, rendering, routes, browser and accessibility checks
  run within the required lint context.
- Two inherited gate defects are corrected: pure `finally` cleanup is not
  exception fallback, and unsupported Pyright options cannot masquerade as controls.
- Initial typing, module, coverage and runtime baselines are measured against
  this adoption, then ratcheted. Strict typing debt is recorded in the debt register.
- Release creation and PyPI publication follow successful master verification
  automatically; token-only upload replaces the inherited password path.
  Merge review supplies authorization without another deployment reviewer.
- Random generation is Chances declared purpose. Bounded fixtures are explicit
  fixtures; fabricated research observations and execution evidence remain forbidden.

## Configured versus active

Initial inspection on 2026-10-01 found no live rulesets or repository variables.
The historical PyPI username/password secrets exist; organization PyPI secrets
are also available. No privileged audit credential was present. Named template
reviewers `zero-bang`, `pdey` and `bit-mis` had read access. Full collaborator
inspection also found `EnergyGuy3` with administrative access alongside
`mikkokotila`; the initial named-reviewer inspection did not establish the
complete administrator inventory.

The operator subsequently authorized GitHub activation. `Protect-Master`
ruleset `24303910` is active and `RULESET_ID` is configured. Exact live comparison
and the privileged local audit pass: all ten required contexts and review rules
match, including an empty bypass list. This proves current server settings,
not execution of the proposed workflows or proof of the scoped organization token.

Branch-restricted `release` and `pypi` environments admit only `master`, disable
administrator bypass, and require no additional reviewer as authorized on
2026-10-03. Operator-confirmed organization `PYPI_API_TOKEN` is validated only
in the isolated upload job. GitHub provenance remains independently attested;
PyPI digital attestations are disabled in token mode. The automatic workflow
chain becomes available after its reviewed change merges.

Sole global CODEOWNER `* @bit-mis` requires the operator
for every PR after merge. The operator confirmed organization `RULESET_AUDIT_TOKEN`;
its actual bypass visibility and authoritative CI for each new commit remain
acceptance prerequisites. Publishing and merge readiness are recorded separately;
no package release is implied. GitHub enforces the sole code owner through required
ownership review; deployment does not request another approval.

## Required evidence

Before acceptance, run product and governance suites, quality gates, locked
dependency checks, deterministic artifact validation and the full docs check.
Preserve exact measured baselines and seeded equivalence results. A failed gate
is a named defect or policy conflict to resolve, not a reason to disable a family.

## Read next

- [Activation runbook](https://github.com/autonomio/chances/blob/master/SETUP.md)
- [Configuration](Configuration.md)
- [Security assurance case](Security-Assurance-Case.md)
