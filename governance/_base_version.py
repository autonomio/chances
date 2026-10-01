"""Read historical Hatch metadata from a protected Git commit without executing it."""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import PurePosixPath

from _common import REPO_ROOT, TOMLDecodeError, fail_setup, loads_toml

BANNER = 'VERSION GATE'


def _git(arguments: list[str]) -> str:
    result = subprocess.run(['git', *arguments], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        fail_setup(BANNER, f'cannot read protected-base version: {result.stderr.strip()}')
    return result.stdout


def hatch_literal_version(pyproject_text: str, base_ref: str) -> str:
    """Accept one top-level literal version only from the declared historical file."""
    commit = _git(['rev-parse', '--verify', '--end-of-options', f'{base_ref}^{{commit}}']).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        fail_setup(BANNER, 'protected base did not resolve to a commit SHA')
    if _git(['show', f'{commit}:pyproject.toml']) != pyproject_text:
        fail_setup(BANNER, 'base pyproject does not match the protected Git commit')
    try:
        data = loads_toml(pyproject_text)
    except TOMLDecodeError as exc:
        fail_setup(BANNER, f'cannot parse protected-base pyproject: {exc}')
    project = data.get('project', {})
    dynamic = project.get('dynamic') if isinstance(project, dict) else None
    if not isinstance(dynamic, list) or dynamic.count('version') != 1 or 'version' in project:
        fail_setup(BANNER, 'protected base must declare one dynamic version without a static conflict')
    tool = data.get('tool', {})
    hatch = tool.get('hatch', {}) if isinstance(tool, dict) else {}
    config = hatch.get('version', {}) if isinstance(hatch, dict) else {}
    if not isinstance(config, dict) or set(config) != {'path'}:
        fail_setup(BANNER, 'protected-base Hatch version must declare only its literal source path')
    source = config['path']
    path = PurePosixPath(source) if isinstance(source, str) else None
    if (path is None or path.is_absolute() or '..' in path.parts or path.suffix != '.py'
            or source != path.as_posix() or '\\' in source or '\x00' in source or ':' in source):
        fail_setup(BANNER, 'protected-base Hatch path must be a safe repository-relative .py file')
    if _git(['ls-tree', '--format=%(objectmode) %(objecttype)', commit, '--', source]).strip() not in {'100644 blob', '100755 blob'}:
        fail_setup(BANNER, 'protected-base version source must be a regular Git blob')
    try:
        tree = ast.parse(_git(['show', f'{commit}:{source}']))
    except SyntaxError as exc:
        fail_setup(BANNER, f'cannot parse protected-base version source: {exc}')
    writes = [node for node in ast.walk(tree) if isinstance(node, ast.Name)
              and node.id == '__version__' and isinstance(node.ctx, (ast.Store, ast.Del))]
    assignments = []
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if len(targets) == 1 and isinstance(targets[0], ast.Name) and targets[0].id == '__version__':
            assignments.append(node)
    if len(writes) != 1 or len(assignments) != 1:
        fail_setup(BANNER, 'protected-base version must have exactly one top-level assignment')
    value = assignments[0].value
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        fail_setup(BANNER, 'protected-base version must be a literal string')
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value.value):
        fail_setup(BANNER, 'protected-base literal version must be canonical MAJOR.MINOR.PATCH')
    return value.value
