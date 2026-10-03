#!/usr/bin/env python3
"""Publish one reviewed, immutable release from the default branch.

Before any tag or release mutation, the workflow event, checked-out SHA,
remote branch, repository identity and existing tag targets must agree.
Notes are the newest matching changelog section plus computed traceability.
A partial publication resumes without moving an existing tag.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib

BANNER: Final[str] = 'CREATE RELEASE'
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
TAG_RE: Final[re.Pattern[str]] = re.compile(r'^v\d+\.\d+\.\d+$')


def run(*args: str) -> str:
    """Run a command and return its stdout, failing loudly on a non-zero exit."""
    result = subprocess.run(args, capture_output=True, text=True, check=False, cwd=REPO_ROOT)
    if result.returncode != 0:
        raise SystemExit(f'{BANNER}: {" ".join(args)} failed: {result.stderr.strip()}')
    return result.stdout.strip()


def current_version() -> str:
    """Read `[project].version` from pyproject.toml."""
    data = tomllib.loads((REPO_ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    version = data.get('project', {}).get('version')
    if not isinstance(version, str) or not version:
        raise SystemExit(f'{BANNER}: pyproject.toml has no [project].version')
    return version


def compute_tag(version: str) -> str:
    """Derive the release tag and reject anything not `vMAJOR.MINOR.PATCH`."""
    tag = f'v{version}'
    if not TAG_RE.match(tag):
        raise SystemExit(f'{BANNER}: {tag!r} does not match {TAG_RE.pattern}')
    return tag


def newest_changelog_section(version: str) -> str:
    """Return the changelog body for this version, without its header."""
    text = (REPO_ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    header = re.compile(r'^#\s+v([0-9A-Za-z.+\-]+)\b')
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if header.match(line)), None)
    if start is None:
        raise SystemExit(f'{BANNER}: CHANGELOG.md carries no version header')
    found = header.match(lines[start])
    if found is None or found.group(1) != version:
        raise SystemExit(
            f'{BANNER}: newest changelog header is {found.group(1) if found else None!r}, '
            f'expected {version!r}'
        )
    body: list[str] = []
    for line in lines[start + 1:]:
        if header.match(line):
            break
        body.append(line)
    return '\n'.join(body).strip()


def previous_tag(tag: str) -> str | None:
    """Return the release tag before this one, or None for a first release."""
    tags = [t for t in run('git', 'tag', '--list', 'v*').splitlines() if TAG_RE.match(t)]
    ordered = sorted(
        (t for t in tags if tuple(map(int, t[1:].split('.'))) < tuple(map(int, tag[1:].split('.')))),
        key=lambda t: tuple(int(part) for part in t[1:].split('.')),
    )
    return ordered[-1] if ordered else None


def traceability(repo: str, tag: str, previous: str | None) -> str:
    """Build the merged-PR list, compare link and changelog anchor."""
    span = f'{previous}..HEAD' if previous else 'HEAD'
    subjects = run('git', 'log', span, '--merges', '--pretty=%s').splitlines()
    numbers = sorted({int(m.group(1)) for s in subjects
                      if (m := re.search(r'#(\d+)', s)) is not None})
    lines = ['', '## Traceability', '']
    if numbers:
        lines.append('Merged pull requests: ' + ', '.join(f'#{n}' for n in numbers))
    else:
        lines.append('Merged pull requests: none since the previous tag')
    if previous:
        lines.append(f'Compare: https://github.com/{repo}/compare/{previous}...{tag}')
    anchor = tag.replace('.', '')
    lines.append(f'Changelog: https://github.com/{repo}/blob/{tag}/CHANGELOG.md#{anchor}')
    return '\n'.join(lines)


def approved_source(repo: str) -> str:
    """Reject unapproved events, stale refs, foreign remotes and dirty bytes."""
    event_name = os.environ.get('GITHUB_EVENT_NAME')
    if event_name not in {'workflow_dispatch', 'workflow_run'}:
        raise SystemExit(f'{BANNER}: publication requires dispatch or validated master workflow')
    if event_name == 'workflow_run':
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())['workflow_run']
        if (event['name'] != 'Verify and build' or event['event'] != 'push'
                or event['status'] != 'completed' or event['conclusion'] != 'success'
                or event['head_branch'] != 'master' or event['head_sha'] != os.environ.get('GITHUB_SHA')
                or event['head_repository']['full_name'] != repo):
            raise SystemExit(f'{BANNER}: upstream workflow does not authorize this source')
    if os.environ.get('GITHUB_REF') != 'refs/heads/master':
        raise SystemExit(f'{BANNER}: publication requires refs/heads/master')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise SystemExit(f'{BANNER}: invalid GITHUB_REPOSITORY')
    origin = run('git', 'remote', 'get-url', 'origin').removesuffix('.git')
    expected = {f'https://github.com/{repo}', f'git@github.com:{repo}'}
    if origin.casefold() not in {value.casefold() for value in expected}:
        raise SystemExit(f'{BANNER}: origin does not match GITHUB_REPOSITORY')
    head = run('git', 'rev-parse', 'HEAD')
    if head != os.environ.get('GITHUB_SHA') or not re.fullmatch(r'[0-9a-f]{40}', head):
        raise SystemExit(f'{BANNER}: HEAD does not equal the approved dispatch SHA')
    remote = run('git', 'ls-remote', 'origin', 'refs/heads/master').split()
    if len(remote) != 2 or remote[0] != head or remote[1] != 'refs/heads/master':
        raise SystemExit(f'{BANNER}: remote master changed after approval')
    if run('git', 'status', '--porcelain'):
        raise SystemExit(f'{BANNER}: release checkout contains uncommitted files')
    return head


def tag_targets(tag: str) -> tuple[str | None, str | None]:
    """Resolve local and remote annotated or lightweight tags to commits."""
    local = run('git', 'tag', '--list', tag)
    local_commit = run('git', 'rev-parse', f'{tag}^{{commit}}') if local else None
    lines = run('git', 'ls-remote', '--tags', 'origin',
                f'refs/tags/{tag}', f'refs/tags/{tag}^{{}}').splitlines()
    refs = {}
    for line in lines:
        commit, reference = line.split()
        refs[reference] = commit
    remote_commit = refs.get(f'refs/tags/{tag}^{{}}') or refs.get(f'refs/tags/{tag}')
    return local_commit, remote_commit


def release_exists(repo: str, tag: str) -> bool:
    """Distinguish absent releases from API/authentication failures."""
    result = subprocess.run(
        ['gh', 'api', f'repos/{repo}/releases/tags/{tag}'],
        capture_output=True, text=True, check=False, cwd=REPO_ROOT,
    )
    if result.returncode == 0:
        return True
    if 'HTTP 404' in result.stderr:
        return False
    raise SystemExit(f'{BANNER}: cannot read release: {result.stderr.strip()}')


def main() -> int:
    """Publish the approved SHA; refuse to move a conflicting existing tag."""
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not repo:
        raise SystemExit(f'{BANNER}: GITHUB_REPOSITORY is not set')
    head = approved_source(repo)
    version = current_version()
    if os.environ.get('REQUESTED_VERSION') != version:
        raise SystemExit(f'{BANNER}: REQUESTED_VERSION must equal the project version')
    tag = compute_tag(version)
    notes = newest_changelog_section(version)
    if not notes:
        raise SystemExit(f'{BANNER}: changelog section for {version} is empty')
    local, remote = tag_targets(tag)
    if any(commit != head for commit in (local, remote) if commit is not None):
        raise SystemExit(f'{BANNER}: existing {tag} points outside the approved SHA')
    released = release_exists(repo, tag)
    if released and remote is None:
        raise SystemExit(f'{BANNER}: release exists without its remote tag')
    if remote is not None and released:
        print(f'{BANNER} -- SKIP ({tag} is already tagged and released)')
        return 0
    body = notes + '\n' + traceability(repo, tag, previous_tag(tag))
    if local is None and remote is None:
        run('git', 'tag', '-a', tag, '-m', tag)
    if remote is None:
        run('git', 'push', 'origin', f'refs/tags/{tag}')
    with tempfile.TemporaryDirectory(prefix='chances-release-') as directory:
        notes_path = Path(directory) / 'release-notes.md'
        notes_path.write_text(body, encoding='utf-8')
        run('gh', 'release', 'create', tag, '--repo', repo,
            '--title', tag, '--notes-file', str(notes_path), '--verify-tag')
    print(f'{BANNER} -- PASS (released {tag})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
