"""Supply-chain law: workflow actions are pinned by commit SHA and
checkout credentials are never persisted.

One assertion per law over every workflow file, so a regression in any
one of them reds the required tests gate:

  1. Every ``uses:`` reference is pinned to a full 40-hex commit SHA
     with a trailing ``# vX.Y.Z`` comment naming the tag it was
     resolved from. A mutable tag (``@v5``) or branch reference can be
     repointed upstream after review; a commit SHA cannot.
  2. Every ``actions/checkout`` step sets ``persist-credentials:
     false``. The default persists a repo-scoped token into
     ``.git/config`` for every later step in the job; no template
     workflow pushes with that credential (bootstrap pushes through an
     explicit token remote), so nothing may keep it.
  3. Every workflow declares an explicit ``permissions:`` block at the
     workflow or job level, so no job runs on the org default grant.
  4. Every ``git fetch`` a workflow runs authenticates per command via
     an ``http.<host>.extraheader`` ``-c`` flag: with credential
     persistence off, a bare fetch works only in public repos and
     breaks in private derived repositories.

And the install law over every ``pip install`` a workflow runs:

  5. Every install is either a hash-locked compiled set
     (``--require-hashes -r requirements/ci/<set>.txt``) or the
     first-party editable install with resolution disabled
     (``--no-build-isolation --no-deps -e .``), so no job resolves a
     third-party package outside the hash-pinned sets. The declared
     runtime dependencies the ``--no-deps`` install skips come from
     the ``runtime-env`` set, which mirrors ``[project.dependencies]``.
  6. Every compiled set is hash-complete (each requirement entry
     carries at least one ``--hash=sha256``) and every ``.in`` source
     has its compiled ``.txt`` sibling and vice versa.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from _common import REPO_ROOT
from _locked_requirements import locked_requirements

WORKFLOWS_DIR = REPO_ROOT / '.github' / 'workflows'
REQUIREMENTS_DIR = REPO_ROOT / 'requirements' / 'ci'

PINNED_USES_RE = re.compile(r'^\s*(?:- )?uses: \S+@[0-9a-f]{40}\s+# v\d+\.\d+\.\d+$')
ANY_USES_RE = re.compile(r'^\s*(?:- )?uses: ')
CHECKOUT_RE = re.compile(r'^\s*(?:- )?uses: actions/checkout@')
NEXT_STEP_RE = re.compile(r'^\s*- (?:name|uses|run|env|id|if):')
PERMISSIONS_RE = re.compile(r'^(?:permissions:|    permissions:)', re.MULTILINE)
PERSIST_LINE_RE = re.compile(r'^\s*persist-credentials: false\s*$')
# Deliberately exempts exactly one canonical spelling: like the byte-equal
# title rule, the law pins the form itself, so a differently-formatted
# compliant fetch fails loud and gets rewritten to canon rather than
# growing regex permutations here.
GIT_FETCH_RE = re.compile(r'^\s*git (?!-c "http\.https://github\.com/\.extraheader=\$AUTH" )[^|]*\bfetch\b')
# Anchored across the whole stripped line (an optional inline `run:`
# prefix and the interpreter/uv prefix included), so a non-compliant
# install cannot hide chained ahead of a compliant tail.
INSTALL_PREFIX = r'(?:run: )?(?:(?:[\w./-]+|"\$chances_smoke_env/bin/python") -m |uv )?'
HASHED_INSTALL_RE = re.compile(
    INSTALL_PREFIX
    + r'pip install (?:--python \S+ )?--require-hashes -r requirements/ci/[a-z-]+\.txt'
)
# Installing a distribution the workflow just built is not a dependency
# resolution: the artifact comes from `dist/`, not an index, and proving it
# installs and imports is exactly what the packaging job exists for. There is
# nothing to hash-lock.
BUILT_ARTIFACT_INSTALL_RE = re.compile(
    INSTALL_PREFIX + r'pip install --no-build-isolation --no-deps (?:dist/\*\.whl|"\$artifact")'
)
EDITABLE_INSTALL_RE = re.compile(
    INSTALL_PREFIX
    + r'pip install (?:--python \S+ )?--no-build-isolation --no-deps -e \.'
)


def _workflow_files() -> list[Path]:
    files = sorted(WORKFLOWS_DIR.glob('*.yml'))
    assert files, f'no workflow files found under {WORKFLOWS_DIR}'
    return files


def test_every_action_reference_is_sha_pinned() -> None:
    violations: list[str] = []
    for path in _workflow_files():
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if ANY_USES_RE.match(line) and not PINNED_USES_RE.match(line):
                violations.append(f'{path.name}:{lineno}: {line.strip()}')
    assert not violations, (
        'workflow action references must be pinned to a full commit SHA '
        'with a `# vX.Y.Z` tag comment:\n' + '\n'.join(violations)
    )


def test_every_checkout_disables_credential_persistence() -> None:
    violations: list[str] = []
    for path in _workflow_files():
        lines = path.read_text(encoding='utf-8').splitlines()
        for lineno, line in enumerate(lines, start=1):
            if not CHECKOUT_RE.match(line):
                continue
            step_end = lineno
            while step_end < len(lines) and not NEXT_STEP_RE.match(lines[step_end]):
                step_end += 1
            if not any(PERSIST_LINE_RE.match(entry) for entry in lines[lineno - 1:step_end]):
                violations.append(f'{path.name}:{lineno}: checkout without persist-credentials: false')
    assert not violations, '\n'.join(violations)


def _run_blocks(path: Path) -> list[str]:
    payload = yaml.safe_load(path.read_text())
    return [step['run'] for job in payload['jobs'].values() for step in job.get('steps', [])
            if isinstance(step.get('run'), str)]


def _fetch_violations(program: str) -> list[str]:
    active = set()
    declarations = {
        'GIT_CONFIG_COUNT': 'export GIT_CONFIG_COUNT=1',
        'GIT_CONFIG_KEY_0': 'export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader',
        'GIT_CONFIG_VALUE_0': 'export GIT_CONFIG_VALUE_0="$AUTH"',
    }
    failures = []
    for line in program.splitlines():
        stripped = line.strip()
        for variable, declaration in declarations.items():
            if variable in stripped and (stripped.startswith('export ') or stripped.startswith('unset ')):
                active.discard(variable)
                if stripped == declaration:
                    active.add(variable)
        if GIT_FETCH_RE.match(line) and active != set(declarations):
            failures.append(stripped)
    return failures


def test_every_git_fetch_authenticates_per_command() -> None:
    violations = [f'{path.name}: {line}' for path in _workflow_files()
                  for program in _run_blocks(path) for line in _fetch_violations(program)]
    assert not violations, 'git fetch requires ephemeral HTTP authentication:\n' + '\n'.join(violations)


def test_ephemeral_fetch_auth_cannot_hide_a_missing_or_reset_header() -> None:
    declarations = ('export GIT_CONFIG_COUNT=1\n'
                    'export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader\n'
                    'export GIT_CONFIG_VALUE_0="$AUTH"\n')
    assert _fetch_violations(declarations + 'git fetch origin master') == []
    assert _fetch_violations('git fetch origin master')
    for marker in ('export GIT_CONFIG_COUNT=0', 'unset GIT_CONFIG_KEY_0',
                   'export GIT_CONFIG_VALUE_0=""'):
        assert _fetch_violations(declarations + marker + '\ngit fetch origin master')


def test_every_workflow_declares_permissions() -> None:
    # Column 0 is the workflow-level key and a four-space indent is the
    # job-level key; deeper matches (e.g. the word inside a run block)
    # do not count as a permissions declaration.
    violations: list[str] = []
    for path in _workflow_files():
        if not PERMISSIONS_RE.search(path.read_text(encoding='utf-8')):
            violations.append(f'{path.name}: no permissions block at workflow or job level')
    assert not violations, '\n'.join(violations)


def test_every_workflow_install_is_hash_locked() -> None:
    violations: list[str] = []
    for path in _workflow_files():
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if 'pip install' not in line or line.lstrip().startswith('#'):
                continue
            stripped = line.strip()
            if (
                HASHED_INSTALL_RE.fullmatch(stripped)
                or EDITABLE_INSTALL_RE.fullmatch(stripped)
                or (BUILT_ARTIFACT_INSTALL_RE.fullmatch(stripped)
                    and ('"$artifact"' not in stripped or
                         'for artifact in dist/*.whl dist/*.tar.gz; do' in path.read_text()))
            ):
                continue
            violations.append(f'{path.name}:{lineno}: {stripped}')
    assert not violations, (
        'workflow installs must use a hash-locked set or the '
        'no-resolution editable form:\n' + '\n'.join(violations)
    )


def test_requirement_sets_are_hash_complete_and_paired() -> None:
    sources = sorted(REQUIREMENTS_DIR.glob('*.in'))
    compiled = sorted(REQUIREMENTS_DIR.glob('*.txt'))
    assert sources, f'no requirement sources under {REQUIREMENTS_DIR}'
    assert [p.stem for p in sources] == [p.stem for p in compiled]

    for path in compiled:
        assert locked_requirements(path.read_text(encoding='utf-8')), path


@pytest.mark.parametrize('entry', [
    'numpy', 'numpy>=2', 'numpy==2',
    'chances @ file:///Users/person/dev/chances', '-e .', '../local-project',
    '--extra-index-url https://example.invalid', '-r nested.txt',
    'numpy==2.*', 'numpy @ https://example.invalid/numpy.whl',
    'numpy==2 --hash=sha256:bad',
])
def test_hash_check_cannot_skip_an_unpinned_or_local_entry(entry: str) -> None:
    valid = 'scipy==1.15 --hash=sha256:' + 'a' * 64 + '\n'
    with pytest.raises(ValueError):
        locked_requirements(valid + entry + '\n')


def test_hashes_do_not_make_direct_urls_or_unpinned_entries_acceptable() -> None:
    for requirement in ('numpy>=2', 'numpy==2.*', 'chances @ file:///Users/person/chances'):
        with pytest.raises(ValueError):
            locked_requirements(requirement + ' --hash=sha256:' + 'a' * 64)
    pinned = 'numpy==2; python_version >= "3.10" --hash=sha256:' + 'a' * 64
    assert next(iter(locked_requirements(pinned).values())).name == 'numpy'


def test_every_job_running_a_repo_file_checks_out_the_repository() -> None:
    """A job that executes a tracked file must first check the repository out.

    Most guard jobs reach GitHub entirely through `gh` against
    `$GITHUB_REPOSITORY` and need no working tree, so a missing checkout is
    invisible until a step runs something from disk -- and then it fails with
    `can't open file`, which for `slice_closeout_guard` means reopening a
    correctly merged slice. No unit test can see this: the failure is in the
    job's composition, not in any module the job calls.
    """
    tracked_dirs = ('governance/', 'scripts/', 'tests/')
    offenders: list[str] = []
    for path in sorted(WORKFLOWS_DIR.glob('*.yml')):
        workflow = yaml.safe_load(path.read_text(encoding='utf-8'))
        for job_name, job in (workflow.get('jobs') or {}).items():
            steps = job.get('steps') or []
            has_checkout = any(
                isinstance(s.get('uses'), str) and s['uses'].startswith('actions/checkout@')
                for s in steps
            )
            if has_checkout:
                continue
            for step in steps:
                run = step.get('run')
                if not isinstance(run, str):
                    continue
                for line in run.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        continue
                    if any(f' {d}' in f' {stripped}' for d in tracked_dirs):
                        offenders.append(
                            f'{path.name}:{job_name} runs `{stripped}` with no checkout'
                        )
                        break
                else:
                    continue
                break
    assert not offenders, '\n'.join(offenders)
