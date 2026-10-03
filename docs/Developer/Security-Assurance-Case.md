# Security assurance case

This page states the evidence and limits of Chances security controls.
[SECURITY.md](../../SECURITY.md) owns vulnerability reporting;
[governance adoption](Governance-Adoption.md) distinguishes configured and live controls.

## Prerequisites

Read the scientific [receipt contract](../Reference/Specifications-and-Receipts.md)
and the repository [constitution](../../CLAUDE.md). Verification uses Python 3.12
and GitHub CLI; remote claims require live repository evidence.

## Threat model and security requirements

An attacker may control specification JSON, source arrays, saved bundles,
issue text, or proposed repository changes. Their goals include executing
input code, exhausting resources, changing retained results without detection,
overwriting an existing batch, or introducing an unauthorized release.
An accidental invalid scientific request is subject to the same validation.

Chances must reject unsupported syntax and values, bound declared work,
preserve caller-owned inputs and global RNG state, detect altered bundle
content, refuse incompatible replay, and publish a batch without replacing an
existing destination. It must expose failures rather than select a different
scientific method. These claims assume a trusted Python/runtime installation,
filesystem and reviewed implementation; they do not cover compromised hardware
or an attacker who controls the host process. Resource limits bound declared
arrays and work, not every possible native-library execution time.

The [receipt contract](../Reference/Specifications-and-Receipts.md) owns the
user-visible guarantees and compatibility conditions. An attacker who rewrites
all unsigned bundle content and hashes can create a consistent replacement;
hash verification detects integrity mismatch, not authorship or authenticity.

## Trust boundaries

| Boundary | Evidence and limit |
| --- | --- |
| Scientific specification and source | strict literal JSON/array validation, finite values, bounded resources; no pickle or callbacks |
| Receipt bundle | content hashes, protocol checks, owned stream and environment evidence; unsigned integrity, not authenticity |
| Issue and PR text | parser property tests and slice contracts; untrusted text never grants tool authorization |
| Merge | ten required checks and sole `bit-mis` approval; the privileged ruleset audit passed on merged master |
| Dependencies | bound manifest, CI hashes, runtime vulnerability gate and explicit expiring exceptions |
| Documentation dependencies | complete-tree audit blocks every known advisory, including development tools |
| Actions | SHA-pinned actions, limited permissions, untrusted PR code separated from credentialed mutation |
| Publication | exact master identity, master-only environments without additional reviewers, isolated organization PyPI API token, and GitHub build attestations after successful runs |

## Secure-design argument

| Principle | Applied control and evidence |
| --- | --- |
| Fail-safe defaults | Invalid fields, seeds, source types and limits fail before generation; replay rejects incompatible evidence. See [protocol validation](../../chances/_api.py) and [stream resolution](../../chances/_random.py). |
| Complete mediation | Public inspection and generation resolve inputs through the shared validator; archive verification checks recorded contracts and content before replay. [API tests](../../tests/package) exercise both accepted and rejected inputs. |
| Least privilege and separation | Library calls need no credentials or network service. Workflow defaults are read-only; credentialed publication follows verified master workflows after protected merge review. [Workflow contract tests](../../governance/tests/test_openssf_workflows.py) prohibit default write permissions. |
| Economy of mechanism | Literal JSON, typed arrays and one protocol route avoid executable input formats. Generation, verification and replay share explicit contracts instead of unrelated shortcuts. |
| Open design | Source, schemas, tests, governance rules and this argument are public. Receipts use published SHA-256 rather than a private cryptographic construction. |
| Least common mechanism | Each declared stream owns a local generator; [randomness implementation](../../chances/_random.py) and package tests enforce independence from global RNG state. |
| Psychological acceptability | Inspection reveals resolved choices before drawing; structured failures identify corrections. [Python API](../Reference/README.md) and [quick start](../../README.md#first-successful-computation) show the same path used by agents. |

## Common-weakness argument

| Weakness class | Countermeasure and limit |
| --- | --- |
| Injection and unsafe deserialization (CWE-94, CWE-502) | No input callbacks, code evaluation or pickle. Array loading uses `allow_pickle=False`; literal JSON and dtype allowlists define accepted data. See [input handling](../../chances/_api.py). |
| Improper validation and resource exhaustion (CWE-20, CWE-400) | Validate domains, finite values, array shape, supported dtype and declared resource limits before drawing; check output contracts afterward. [Scientific tests](../../tests/package) and [protocol fuzzing](../../fuzz/fuzz_protocol.py) exercise malformed and extreme inputs. |
| Race and unintended overwrite (CWE-362, CWE-367) | Build a batch in a temporary sibling and publish without replacing an existing destination. [Publication implementation](../../chances/_publication.py) and package tests cover contention and retained evidence. A hostile host/filesystem remains outside the guarantee. |
| Incorrect security assumptions (CWE-345) | Receipt checks bind content and protocol but explicitly make no signature claim. Replay checks the recorded environment; a successful check does not prove scientific suitability. |
| Vulnerable dependencies and unauthorized changes | Locked tooling, runtime and documentation audits, CodeQL, required reviews and live ruleset checks constrain the supply chain. [Dependency policy](Release-Policy.md) and [governance adoption](Governance-Adoption.md) state activation and historical limits. Unknown vulnerabilities and compromised trusted accounts remain risks. |

## Mechanical proof

The honesty suite binds configuration, laws and required-check snapshot. Mutation
tests assert that removed controls fail. The ruleset gate compares live protection
and the privileged post-merge audit additionally inspects bypass actors.
Ruff enforces code shape; Pyright and fail-loud patterns cannot grow beyond their
measured adoption baseline. Baseline debt remains visible, not silently erased.
Coverage, module size, file balance, test/code ratio, changed-line coverage and
runtime budgets measure distinct constraints; passing one does not prove the others.

Scientific tests cover declared supports, structure, global RNG isolation, source
preservation, receipt tampering and replay. They do not prove every distribution
law from a finite array or choose a scientifically suitable method for a researcher.

## Verification

```bash
python -m pytest governance/tests -q
python -m pytest tests/package -q
gh api repos/autonomio/chances/rulesets
gh attestation verify <artifact> --repo autonomio/chances
```

Local tests prove the candidate checkout. GitHub CI, repository settings and
artifact attestations require separate evidence after publication and activation.

## OpenSSF evidence

[Best Practices entry 15137](https://www.bestpractices.dev/projects/15137)
records the Passing badge earned on 2026-10-01. `.bestpractices.json` retains
criterion statuses and source-linked evidence; it distinguishes maintainer
attestations from measured checks. Silver requires separate evidence.
The live Silver assessment is 93% as of 2026-10-03. A progress percentage
includes unanswered criteria and does not measure implemented security controls.
The signed-release criterion is supported by the published
[2.0.7 release](https://github.com/autonomio/chances/releases/tag/v2.0.7),
its complete-source and distribution signature bundles, and consumer verification
against source `da0e7ba01e5b4f9b6c15afb48c2cfb489c84ac1f`.
Freshly downloaded PyPI distributions match the signed GitHub assets.
[Release policy](Release-Policy.md) owns the public verification commands.

### Dependency repair

The documentation toolchain carries local source backports for the two unpatched
upstream advisories. Brace parsing and direct AST walkers reject excessive depth
before recursion and reject cyclic child or parent links. Cache evaluation
and origin-error revalidation refuse security-blocked responses before
honoring `max-stale`, stale-while-revalidate or stale-if-error. Upstream licenses, registry
integrity and original/patched file digests remain in `docs-site/vendor/`.
These are maintained Autonomio patches, not upstream releases or risk acceptance.

The required documentation gate tests the reported attacks, normal behavior,
installed consumer resolution and source integrity. `security:audit` verifies
backport identity and hashes before scanning the full locked tree. A clean
installation reported zero registry findings on 2026-10-03, with no active
advisory exceptions. Registry scanners do not establish the safety of local
forks: the source diffs and exploit regressions supply that evidence. Remove the
overrides only after upstream replacements pass the same regressions.
The pip/urllib3 lock repairs are already merged in PRs 48 and 50.
The scientific wheel carries none of this Node tooling.

### Six-month regression audit

The audit window is 2026-04-03 through 2026-10-03, ending at protected-master
commit `da0e7ba01e5b4f9b6c15afb48c2cfb489c84ac1f`. Its complete public history
contains eight merged PRs and 42 non-merge commits. Read every change, including
build, test and CI subjects; a `fix:` prefix is not the denominator.
Count distinct project defects, coalesce follow-up repair/test commits for one
defect, and exclude new capability and prose-only changes. Dependency advisories
in third-party implementations are assessed in the dependency criterion; this
table covers Chances-authored product, governance, packaging and documentation
defects, including defects repaired before the adoption PR was merged.

The public audit identifies 38 defects; 31 have added or expanded automated
regression cases (81.6%). A pre-existing passing gate alone is not counted.
Rows without a demonstrated new regression case remain in the denominator.
This exceeds 50% for public history; confirmation that no private fixes are
missing is still required before claiming the whole-project criterion.

| Distinct defect | Fix commit(s) | Added or expanded regression case |
|---|---|---|
| Missing editable build backend | `19aeab7` | `governance/tests/test_toolchain_locks.py::test_editable_backend_is_available_on_every_ci_target` |
| Missing Linux keyring transitive locks | `19aeab7` | `governance/tests/test_toolchain_locks.py::test_linux_packaging_lock_contains_keyring_transitive_dependencies` |
| Publication destination race overwrites | `634e984` | `tests/package/test_publication.py::test_atomic_publish_rejects_destination_created_after_last_check` |
| Output parent failures escape structured errors | `634e984` | `tests/package/test_publication.py::test_output_parent_file_produces_structured_error_without_mutation` |
| NUL paths reach native publication | `634e984` | `tests/package/test_publication.py::test_native_c_paths_reject_nul_before_calling_libc` |
| Path-subclass callbacks cross native boundary | `634e984` | `tests/package/test_publication.py::test_native_publication_rejects_path_subclass_callbacks` |
| Unavailable native primitive permits unsafe fallback | `634e984` | `tests/package/test_publication.py::test_unavailable_native_function_fails_explicitly` |
| Unreadable protected budgets disable ratchets | `634e984` | `governance/tests/test_gate_fail_closed.py::test_unreachable_protected_base_fails_setup` |
| Boolean/non-object budgets pass parsing | `634e984` | `governance/tests/test_gate_fail_closed.py::test_malformed_protected_budget_is_a_setup_failure` |
| Invalid runtime numbers or profile rows bypass gates | `634e984` | `governance/tests/test_gate_fail_closed.py::test_invalid_runtime_numbers_fail_setup` |
| Malformed vulnerability exception text accepted | `634e984` | `governance/tests/test_dependency_vulnerabilities.py::test_invalid_reason_cannot_hide_a_known_vulnerability` |
| Public security-report template exposes private reports | `6d7008b` | `governance/tests/test_ci_contract.py::test_security_reporting_has_only_a_private_contact_route` |
| Issue-triggered rerun loses PR author identity | `6d7008b` | `governance/tests/test_sweep_matches_gate.py::test_rerun_reads_the_author_from_the_rest_user_login` |
| Incomplete/error audit JSON fails open | `7949d8a` | `docs-site/tests/audit-report.test.mjs::fails closed on npm audit errors and incomplete reports` |
| Array/non-object audit collections are accepted | `632b374` | `docs-site/tests/audit-report.test.mjs::array vulnerability reports fail closed` |
| Publication crash leaves a permanent reservation | `44ec09e` | `tests/package/test_publication.py::test_hard_crash_during_staging_cannot_reserve_destination` |
| Staging failure escapes the declared error boundary | `44ec09e` | `tests/package/test_execution_boundaries.py::test_staging_failure_is_structured_without_publishing` |
| Scorecard checkout lacks contents read permission | `9708cac` | No new case established |
| Workflow defaults grant write permissions | `5570d98` | No new case established |
| Package and citation versions disagree | `ff226d8` | `governance/tests/test_openssf_workflows.py::test_declared_version_matches_package_and_citation` |
| Consumer requirements import repository enforcement locks | `681b515` | `governance/tests/test_openssf_workflows.py::test_runtime_requirements_preserve_project_envelope` |
| Fuzz oracle accepts mutated receipt metadata | `7fdfb65/4a08629` | `governance/tests/test_fuzz_shutdown.py::test_rehashed_receipt_target_detects_false_acceptance` |
| Atheris watchdog remains armed at shutdown | `7fdfb65` | `governance/tests/test_fuzz_shutdown.py::test_fuzzer_releases_watchdog_without_changing_exit_status` |
| Fuzz installation allows source builds of transitive dependencies | `7fdfb65` | No new case established |
| Manifest checks reject repository badge evidence | `bc8a9d8` | No new case established |
| README example leaves retained evidence in the checkout | `371c241` | `tests/package/test_distribution_artifacts.py::test_readme_example_is_executable` |
| Superseded verification and browser installation occupy runners | `ca68e55/0b0df4a` | `governance/tests/test_ci_capacity.py::test_source_checks_are_bounded_without_losing_required_gates` |
| Remaining source jobs lack cancellation and deadlines | `5353d70/0b0df4a` | `governance/tests/test_ci_capacity.py::test_source_checks_are_bounded_without_losing_required_gates` |
| Empty readiness events allocate a runner | `5353d70/0b0df4a` | `governance/tests/test_ci_capacity.py::test_readiness_skips_empty_suites_before_allocating_a_runner` |
| Publication does not bind complete source to the approved commit | `0b0df4a` | `governance/tests/test_pypi_publish_contract.py::test_source_provenance_is_checked_before_build_and_pypi_handoff` |
| Existing release asset bytes can be replaced | `0b0df4a` | `governance/tests/test_release_assets.py::test_upload_compares_existing_bytes_before_any_mutation` |
| Release controller enters scientific archives | `562ac7e` | No new case established |
| Audit exceptions are not bound to installed identities | `58d2249` | `docs-site/tests/audit-exceptions.test.mjs::every installed copy must match the locked exception version and identity` |
| Browser evidence overwrites retained dependency audit | `56337a1` | `docs-site/tests/audit-security.test.mjs::the audit command handles complete fixture JSON` |
| macOS temporary symlink aliases invalidate CLI audit fixtures | `6f747ef` | No new case established |
| Generated audit evidence enters source distributions | `aff9595` | No new case established |
| Duplicate Authorization header breaks Git release fetch | `4b94811` | `governance/tests/test_automatic_release.py::test_release_git_receives_authorization_header_exactly_once` |
| Version bump before the merge tail is skipped | `fda520c` | `governance/tests/test_automatic_release.py::test_version_bump_before_merge_tail_still_releases` |

Run the mapped Python cases through the required package/governance suites and
the JavaScript cases through `npm --prefix docs-site run test:unit`.
Retain the unmapped rows when extending this audit; new tests can improve future
coverage but must not be presented as historical tests that existed earlier.

### Reporter credit and continuity

The GitHub repository security-advisory API returned no project advisories on
2026-10-03. This is public-source evidence, not proof that no private report was
resolved. `SECURITY.md` requires reporter credit except requested anonymity.
A maintainer must confirm whether any private vulnerability report was resolved
between 2025-10-03 and 2026-10-03 before selecting N/A or naming public credit.
Upstream dependency advisory reporters are credited by their upstream advisories;
they are not represented as reporters of private Chances vulnerabilities.

Repository collaborator inspection on 2026-10-03 confirmed admin access for
`mikkokotila` and `EnergyGuy3`, and write access for `bit-mis`. The automatic
release has already proven that repository automation can publish using stored
organization credentials. Neither observation alone proves emergency legal
authority, organization recovery, or the ability to replace an unavailable sole
reviewing authority within one week. Normal review remains with `bit-mis`.
Document and authorize the continuity procedure in `MAINTAINERS.md` before
marking this criterion Met; no new routine deployment reviewer is needed.

The initial Scorecard run `36887139175` measured `6.2/10` against merged master
`ee6ab1725bcc60bff78ad45b561dbb3d0b9632da`. Its findings drove read-only
workflow defaults, lockfile remediation and protocol/receipt fuzzing. Verify
subsequent scores against their recorded commit; old review, CI and contributor
history cannot be rewritten by a workflow change. Required mutation permissions
remain in their individual jobs.

The bounded Atheris campaign lives in `fuzz/` and runs from
`.github/workflows/fuzz.yml` and the required lint gate with hash-locked tooling.
It exercises malformed
JSON, bounded structured protocols, deterministic generation and receipt
mutation. Only declared `ChancesError` failures count as expected rejection;
other exceptions and failed invariants crash the campaign and retain evidence.
Fuzzing increases exercised input coverage; it does not prove every possible
input safe. Issue-parser Hypothesis tests remain in the required governance
suite.

For current workflow findings and their evidence, use the
[Scorecard viewer](https://scorecard.dev/viewer/?uri=github.com/autonomio/chances).
Signed-release and packaging detection require successful publication evidence;
a configured publishing workflow alone cannot establish either.

## Residual risk

The current receipt is unsigned. Exact replay depends on the recorded environment.
External method suitability, corrupted hardware, compromised dependencies and
maintainer-account compromise are outside the receipt integrity guarantee.
Dependency scans describe known advisories at check time; undiscovered issues
remain possible.

## Read next

- [Governance adoption](Governance-Adoption.md)
- [Release policy](Release-Policy.md)
