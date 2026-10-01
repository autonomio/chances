"""Audit a verified runtime lock without resolving or executing local projects."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from _common import fail_setup
from _locked_requirements import locked_requirements
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

BANNER = 'DEPENDENCY VULNERABILITY GATE'


def audit(declarations: list[str], lock: Path) -> list[dict[str, object]]:
    """Validate direct requirements against the lock and require complete audit evidence."""
    try:
        entries = locked_requirements(lock.read_text(encoding='utf-8'))
        expected = {}
        for req in entries.values():
            if req.marker is None or req.marker.evaluate():
                name = canonicalize_name(req.name)
                if name in expected:
                    raise ValueError(f'multiple active locked versions for {name}')
                expected[name] = next(iter(req.specifier)).version
        for declaration in declarations:
            req = Requirement(declaration)
            if req.url:
                raise ValueError('runtime declarations cannot use direct URLs')
            if req.marker is not None and not req.marker.evaluate():
                continue
            version = expected.get(canonicalize_name(req.name))
            if version is None or version not in req.specifier:
                raise ValueError(f'runtime lock does not satisfy {declaration}')
    except (OSError, InvalidRequirement, ValueError) as exc:
        fail_setup(BANNER, f'invalid runtime lock: {exc}')
    result = subprocess.run(
        [sys.executable, '-m', 'pip_audit', '-r', str(lock), '--require-hashes',
         '--no-deps', '--disable-pip', '--strict', '--format', 'json',
         '--progress-spinner', 'off'], check=False, capture_output=True, text=True,
    )
    diagnostic = result.stderr.strip() or result.stdout.strip() or 'no diagnostic output'
    if result.returncode not in (0, 1) or not result.stdout.strip():
        fail_setup(BANNER, f'pip-audit could not run: {diagnostic}')
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail_setup(BANNER, f'cannot parse pip-audit JSON: {exc}; {diagnostic}')
    if not isinstance(payload, dict) or not isinstance(payload.get('dependencies'), list):
        fail_setup(BANNER, 'pip-audit returned no dependency list')
    dependencies = payload['dependencies']
    observed = {}
    for dep in dependencies:
        if not isinstance(dep, dict) or not isinstance(dep.get('name'), str):
            fail_setup(BANNER, 'pip-audit returned a malformed dependency')
        name = canonicalize_name(dep['name'])
        if name in observed or dep.get('version') != expected.get(name) or not isinstance(dep.get('vulns'), list):
            fail_setup(BANNER, f'pip-audit returned incomplete or mismatched evidence for {name}')
        observed[name] = dep['version']
        for vuln in dep['vulns']:
            if (not isinstance(vuln, dict) or not isinstance(vuln.get('id'), str)
                    or not vuln['id'] or not isinstance(vuln.get('fix_versions'), list)
                    or any(not isinstance(fix, str) for fix in vuln['fix_versions'])):
                fail_setup(BANNER, f'pip-audit returned a malformed vulnerability for {name}')
    if observed != expected:
        fail_setup(BANNER, 'pip-audit omitted locked runtime dependencies')
    if result.returncode == 1 and not any(dep['vulns'] for dep in dependencies):
        fail_setup(BANNER, f'pip-audit failed without vulnerability evidence: {diagnostic}')
    return dependencies
