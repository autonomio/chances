"""Resolve automatic release requests from successful protected-master workflows."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import tomllib


def request(mode: str) -> tuple[str, str, bool]:
    """Reject unrelated events and resolve version without executing event data."""
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    automatic = os.environ['GITHUB_EVENT_NAME'] == 'workflow_run'
    if os.environ['GITHUB_EVENT_NAME'] not in {'workflow_dispatch', 'workflow_run'}:
        raise SystemExit('Release requires dispatch or a successful upstream workflow.')
    if os.environ['GITHUB_REF'] != 'refs/heads/master':
        raise SystemExit('Release requires protected master.')
    sha = os.environ['GITHUB_SHA']
    if automatic:
        upstream = event['workflow_run']
        expected = 'Verify and build' if mode == 'release' else 'Approved Release'
        allowed_events = {'push'} if mode == 'release' else {'workflow_dispatch', 'workflow_run'}
        if (upstream['name'] != expected or upstream['status'] != 'completed'
                or upstream['conclusion'] != 'success' or upstream['event'] not in allowed_events
                or upstream['head_branch'] != 'master' or upstream['head_sha'] != sha
                or upstream['head_repository']['full_name'] != os.environ['GITHUB_REPOSITORY']):
            raise SystemExit('Upstream workflow does not authenticate this master commit.')
    project = tomllib.loads(Path('pyproject.toml').read_text())['project']
    if project['name'] != 'chances':
        raise SystemExit('Release requires the Chances project.')
    version = project['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise SystemExit('Release requires MAJOR.MINOR.PATCH.')
    tag = f'v{version}'
    key, value = ('version', version) if mode == 'release' else ('tag', tag)
    if not automatic and event['inputs'][key] != value:
        raise SystemExit(f'Requested {key} must equal the committed project version.')
    ready = True
    if automatic:
        response = subprocess.run(['git', 'ls-remote', '--tags', 'origin',
                                   f'refs/tags/{tag}', f'refs/tags/{tag}^{{}}'],
                                  check=True, capture_output=True, text=True, timeout=30).stdout
        references = dict(line.split()[::-1] for line in response.splitlines())
        target = references.get(f'refs/tags/{tag}^{{}}') or references.get(f'refs/tags/{tag}')
        if mode == 'publish' and target is None:
            raise SystemExit('Successful release must have created its immutable tag.')
        ready = target is None or target == sha
    return version, tag, ready


def main() -> None:
    """Write validated workflow outputs for the isolated release and build jobs."""
    mode = sys.argv[1]
    if mode not in {'release', 'publish'}:
        raise SystemExit('Expected release or publish mode.')
    version, tag, ready = request(mode)
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write(f'version={version}\ntag={tag}\nready={str(ready).lower()}\n')
    print(f'{mode}: {tag}; publication eligible: {ready}')


if __name__ == '__main__':
    main()
