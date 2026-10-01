"""Contract tests for the package audit's dependency-bound rule.

The bound rule is the one that catches real breakage: an unbounded dependency
lets a resolver change what ships between two builds of the same version. It
is worth its own test because the first implementation reported the exact
class of dependency it exists to catch as compliant.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))

from package_audit import unbounded


def _bounded(spec: str) -> bool:
    """Whether the audit itself considers this spec bounded."""
    return unbounded([spec]) == []


def test_ranges_and_exact_pins_count_as_bounded() -> None:
    """Verify both bound forms are accepted."""
    assert _bounded('pkg>=1,<2')
    assert _bounded('pkg>=1.2.3, <2')
    assert _bounded('pkg==1.2.3')


def test_environment_markers_do_not_supply_the_bound() -> None:
    """Verify a marker's own `==` cannot satisfy the bound rule.

    Matching over the whole requirement string let
    `pkg; python_version=="3.12"` pass: the `==` inside the marker looked like
    an exact pin. That is precisely an unbounded dependency, and reporting it
    as compliant defeated the rule.
    """
    assert not _bounded('pkg; python_version=="3.12"')
    assert not _bounded('pkg>=1; sys_platform=="linux"')
    assert not _bounded('pkg')
    assert not _bounded('pkg>=1')
    # A genuinely bounded spec keeps its bound when a marker follows it.
    assert _bounded('pkg>=1,<2; python_version<"3.11"')


def test_sdist_retains_inspectable_site_sources_but_excludes_enforcement() -> None:
    from package_audit import REQUIRED_SDIST_PATHS, REQUIRED_WHEEL_PATHS, audit_members
    source = set(REQUIRED_SDIST_PATHS) | {'docs-site/src/css/custom.css', 'tests/package/test_api.py'}
    wheel = set(REQUIRED_WHEEL_PATHS) | {'chances-2.0.0.dist-info/METADATA'}
    assert audit_members(source, wheel) == []
    for forbidden in ('governance/slice_gate.py', '.github/workflows/pr_checks_lint.yml',
                      'requirements/ci/gate-tools.txt', 'docs-site/node_modules/library/index.js',
                      'scripts/create_release.py', 'docs-site/build/index.html'):
        findings = audit_members(source | {forbidden}, wheel)
        assert len(findings) == 1 and forbidden in findings[0]
    assert audit_members(source, wheel | {'docs-site/src/css/custom.css'})


def test_missing_consumer_manuals_and_notices_are_reported() -> None:
    from package_audit import REQUIRED_SDIST_PATHS, REQUIRED_WHEEL_PATHS, audit_members
    findings = audit_members(set(REQUIRED_SDIST_PATHS) - {'docs-site/LICENSE'},
                             set(REQUIRED_WHEEL_PATHS) - {'chances/docs/scaffold-LICENSE'})
    assert len(findings) == 2
    assert any('docs-site/LICENSE' in finding for finding in findings)
    assert any('scaffold-LICENSE' in finding for finding in findings)


def test_specifier_order_does_not_change_version_bounds() -> None:
    assert _bounded('pkg<2,>=1')
    assert _bounded('pkg>1,<=2')
    assert _bounded('pkg~=1.2')
    assert not _bounded('pkg==1.*')
    assert not _bounded('pkg @ https://example.org/pkg.whl')


def test_archive_reader_rejects_escaping_paths_duplicate_files_and_links(tmp_path) -> None:
    import io
    import tarfile
    import zipfile

    import pytest
    from package_audit import sdist_members, wheel_members

    wheel = tmp_path / 'unsafe.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr('../chances/__init__.py', b'')
    with pytest.raises(ValueError, match='unsafe path'):
        wheel_members(wheel)
    for entry in ('../root/README.md', '/root/README.md'):
        source = tmp_path / 'unsafe.tar.gz'
        with tarfile.open(source, 'w:gz') as archive:
            info = tarfile.TarInfo(entry)
            info.size = 1
            archive.addfile(info, io.BytesIO(b'x'))
        with pytest.raises(ValueError, match='unsafe path'):
            sdist_members(source)
    source = tmp_path / 'links.tar.gz'
    with tarfile.open(source, 'w:gz') as archive:
        info = tarfile.TarInfo('root/link')
        info.type = tarfile.SYMTYPE
        info.linkname = '../../outside'
        archive.addfile(info)
    with pytest.raises(ValueError, match='no archive links'):
        sdist_members(source)
