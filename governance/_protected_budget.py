"""Read an optional budget blob only after resolving a reachable protected commit."""
from __future__ import annotations

import re
import subprocess

from _common import REPO_ROOT, fail_setup


def _git(arguments: list[str], banner: str) -> str:
    try:
        result = subprocess.run(['git', *arguments], cwd=REPO_ROOT, capture_output=True,
                                text=True, check=False)
    except OSError as exc:
        fail_setup(banner, f'cannot read protected base: {exc}')
    if result.returncode != 0:
        fail_setup(banner, f'protected base is unreadable or unreachable: {result.stderr.strip()}')
    return result.stdout


def protected_budget_text(base_ref: str, banner: str) -> str | None:
    """Distinguish an absent budget from an unfetched ref or a failed Git read."""
    commit = _git(['rev-parse', '--verify', '--end-of-options', f'{base_ref}^{{commit}}'], banner).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        fail_setup(banner, 'protected base did not resolve to a commit SHA')
    kind = _git(['ls-tree', '--format=%(objectmode) %(objecttype)', commit,
                 '--', '.github/budgets.json'], banner).strip()
    if not kind:
        return None
    if kind not in {'100644 blob', '100755 blob'}:
        fail_setup(banner, 'protected budgets.json must be a regular Git blob')
    text = _git(['show', f'{commit}:.github/budgets.json'], banner)
    if not text.strip():
        fail_setup(banner, 'protected budgets.json is empty')
    return text
