#!/usr/bin/env python3
"""Audit installed product bytes and reproducible scientific source artifacts.

The wheel carries Chances and its portable manuals. The sdist additionally
carries canonical documentation, locked site sources and product tests.
Repository enforcement code, credentials and generated dependency trees stay
in Git. Dependency declarations must constrain both ends of their versions.
"""
from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final

import tomllib
from packaging.requirements import Requirement

BANNER: Final[str] = 'PACKAGE AUDIT'
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DIST: Final[Path] = REPO_ROOT / 'dist'
REQUIRED_SDIST_PATHS: Final[frozenset[str]] = frozenset({
    'README.md', 'LICENSE', 'CHANGELOG.md', 'CONTRIBUTING.md', 'SECURITY.md',
    'CITATION.cff', 'NOTICE', 'pyproject.toml', 'docs-site/LICENSE', 'docs-site/package-lock.json',
    'docs-site/docs-map.json', 'docs-site/product-docs.json', 'scripts/build_catalog.py',
    'chances/AGENTS.md', 'chances/docs/scaffold-LICENSE', 'chances/docs/sources.json',
})
REQUIRED_WHEEL_PATHS: Final[frozenset[str]] = frozenset({
    'chances/__init__.py', 'chances/__main__.py', 'chances/AGENTS.md',
    'chances/docs/README.md', 'chances/docs/recipes.md', 'chances/docs/migration.md',
    'chances/docs/operations.json', 'chances/docs/contracts.json',
    'chances/docs/sources.json', 'chances/docs/scaffold-LICENSE',
})
FORBIDDEN_PREFIXES: Final[tuple[str, ...]] = (
    'governance/', '.github/', 'requirements/', 'fuzz/',
)
FORBIDDEN_FILES: Final[frozenset[str]] = frozenset({
    'governance.yml', 'CLAUDE.md', 'AGENTS.md', 'SETUP.md',
    'scripts/package_audit.py', 'scripts/create_release.py',
})
FORBIDDEN_SEGMENTS: Final[frozenset[str]] = frozenset({
    '.git', 'node_modules', '.generated', '.docusaurus', 'build', 'dist',
    'playwright-report', 'test-results', '__pycache__', '.pytest_cache', '.ruff_cache',
})


def version_part(spec: str) -> str:
    """Exclude PEP 508 markers from version-bound evaluation."""
    return spec.split(';', 1)[0].strip()


def sdist_members(path: Path) -> set[str]:
    """Read regular source files, rejecting archive links and escaping paths."""
    with tarfile.open(path, 'r:gz') as archive:
        members = archive.getmembers()
        _validate_paths([member.name for member in members])
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        if len(roots) != 1 or any(member.issym() or member.islnk() for member in members):
            raise ValueError('sdist must have one root and contain no archive links')
        names = [member.name.split('/', 1)[1] for member in members
                 if member.isfile() and '/' in member.name]
    if len(names) != len(set(names)):
        raise ValueError('sdist contains duplicate file paths')
    _validate_paths(names)
    return set(names)


def wheel_members(path: Path) -> set[str]:
    """Read unique, relative wheel entries."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
    if len(names) != len(set(names)):
        raise ValueError('wheel contains duplicate paths')
    _validate_paths(names)
    return set(names)


def _validate_paths(names: list[str]) -> None:
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:
            raise ValueError(f'archive contains an unsafe path: {name!r}')


def unbounded(specs: list[str]) -> list[str]:
    """Require an exact pin or explicit lower and upper version constraints."""
    failures = []
    for spec in specs:
        requirement = Requirement(spec)
        operators = {item.operator for item in requirement.specifier}
        exact = any(item.operator in {'==', '==='} and '*' not in item.version
                    for item in requirement.specifier)
        interval = bool(operators & {'>=', '>'}) and bool(operators & {'<', '<='})
        if requirement.url or not (exact or interval or '~=' in operators):
            failures.append(spec)
    return failures


def unbounded_dependencies() -> list[str]:
    """Check runtime and optional requirements from the canonical project."""
    project = tomllib.loads((REPO_ROOT / 'pyproject.toml').read_text())['project']
    declared = list(project.get('dependencies', []))
    for extra in project.get('optional-dependencies', {}).values():
        declared.extend(extra)
    return unbounded(declared)


def audit_members(source: set[str], wheel: set[str]) -> list[str]:
    """Assert artifact boundaries independently of build inclusion settings."""
    failures = [f'sdist is missing {name}' for name in sorted(REQUIRED_SDIST_PATHS - source)]
    failures.extend(f'wheel is missing {name}' for name in sorted(REQUIRED_WHEEL_PATHS - wheel))
    for kind, names in (('sdist', source), ('wheel', wheel)):
        for name in sorted(names):
            parts = PurePosixPath(name).parts
            if name in FORBIDDEN_FILES or name.startswith(FORBIDDEN_PREFIXES):
                failures.append(f'{kind} ships repository enforcement file {name}')
            elif FORBIDDEN_SEGMENTS.intersection(parts) or any(p.startswith('.venv') for p in parts):
                failures.append(f'{kind} ships generated/local file {name}')
            elif kind == 'wheel' and not (name.startswith('chances/') or '.dist-info/' in name):
                failures.append(f'wheel ships non-product file {name}')
    if 'chances/README.md' in wheel:
        failures.append('wheel ships repository-relative Chances README without portable links')
    return failures


def main() -> int:
    """Audit every built artifact rather than silently choosing the last one."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, nargs='?')
    parser.add_argument('--dist', type=Path)
    args = parser.parse_args()
    if args.directory is not None and args.dist is not None:
        parser.error('choose a positional directory or --dist, not both')
    destination = args.dist or args.directory or DIST
    sdists = sorted(destination.glob('*.tar.gz'))
    wheels = sorted(destination.glob('*.whl'))
    if not sdists or not wheels:
        print(f'{BANNER} -- FAIL: no wheel/sdist pair in {destination}', file=sys.stderr)
        return 2
    failures = []
    for source in sdists:
        failures.extend(audit_members(sdist_members(source), REQUIRED_WHEEL_PATHS))
    for wheel in wheels:
        failures.extend(audit_members(REQUIRED_SDIST_PATHS, wheel_members(wheel)))
    failures.extend(f'dependency {spec!r} lacks lower and upper bounds'
                    for spec in unbounded_dependencies())
    if failures:
        print(f'{BANNER} -- FAIL', file=sys.stderr)
        for failure in failures:
            print(f'  - {failure}', file=sys.stderr)
        return 1
    print(f'{BANNER} -- PASS ({len(sdists)} sdist, {len(wheels)} wheel)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
