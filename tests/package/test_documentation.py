"""Prove canonical ownership, portable installed links and documentation examples."""

from __future__ import annotations

import hashlib
import json
import os
import posixpath
import re
import runpy
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS_MAP = json.loads((ROOT / 'docs-site/docs-map.json').read_text())
SOURCES = [document['source'] for document in DOCS_MAP['documents']]


def _prose(content: str) -> str:
    return re.sub(r'^```[^\n]*\n.*?^```[ \t]*$', '', content, flags=re.M | re.S)


def _links(content: str) -> list[str]:
    prose = _prose(content)
    inline = re.findall(r'\[[^\]\n]*\]\(([^\n)]+)\)', prose)
    references = re.findall(r'^\[[^\]\n]+\]:[ \t]*([^\n]+)$', prose, flags=re.M)
    html = re.findall(r'<(?:a|img)\b[^>]*?\b(?:href|src)=[\"\']([^\"\']+)[\"\']', prose, flags=re.I)
    return [
        re.fullmatch(r'<?([^\s>]+)>?(.*)', target.strip())[1]
        for target in inline + references + html
    ]


def _anchors(content: str) -> set[str]:
    anchors = set(re.findall(r'\bid=[\"\']([^\"\']+)[\"\']', _prose(content)))
    counts: dict[str, int] = {}
    for heading in re.findall(r'^#{1,6} (.+?)[ \t]*#*[ \t]*$', _prose(content), flags=re.M):
        anchor = re.sub(r'[^\w\s-]', '', heading.lower()).replace(' ', '-')
        duplicate = counts.get(anchor, 0)
        counts[anchor] = duplicate + 1
        anchors.add(f'{anchor}-{duplicate}' if duplicate else anchor)
    return anchors


def test_every_maintained_source_has_one_public_route_and_installed_owner():
    expected = {
        'README.md',
        'CHANGELOG.md',
        'docs-site/README.md',
        'chances/README.md',
        'CONTRIBUTING.md',
        'GOVERNANCE.md',
        'MAINTAINERS.md',
        'SECURITY.md',
        'SUPPORT.md',
        'THIRD_PARTY.md',
        'CODE_OF_CONDUCT.md',
    }
    expected.update(path.relative_to(ROOT).as_posix() for path in (ROOT / 'docs').rglob('*.md'))
    assert set(SOURCES) == expected
    assert len(SOURCES) == len(set(SOURCES))
    for key in ('dest', 'slug'):
        values = [document[key] for document in DOCS_MAP['documents']]
        assert len(values) == len(set(values)), key
    assert [section['label'] for section in DOCS_MAP['sections']] == [
        'Overview',
        'Guides',
        'Reference',
        'Developer',
        'Packages',
    ]
    section_routes = {section['slug'] for section in DOCS_MAP['sections']}
    for document in DOCS_MAP['documents']:
        assert (ROOT / document['source']).is_file()
        slug = document['slug']
        assert slug == '/' or '/' + slug.split('/')[1] in section_routes
        assert slug == '/' or not slug.endswith('/')


def test_product_profile_and_installed_manifest_use_the_canonical_identity():
    profile = json.loads((ROOT / 'docs-site/product-docs.json').read_text())
    inventory = json.loads((ROOT / 'chances/docs/sources.json').read_text())
    assert profile['productId'] == 'chances'
    assert profile['productName'] == 'Chances'
    assert profile['sourceRepoUrl'] == 'https://github.com/autonomio/chances'
    assert profile['siteUrl'] == 'https://autonomio.github.io'
    assert profile['basePath'] == '/chances/'
    assert inventory['source_repo_url'] == profile['sourceRepoUrl']
    assert inventory['source_branch'] == profile['sourceBranch']
    assert inventory['entrypoint'] == 'docs/README.md'
    css = (ROOT / 'docs-site/src/css/custom.css').read_text()
    assert '--autonomio-paper:' in css
    assert '--autonomio-ink:' in css
    assert '#F8F8F8' in css.upper() and '#121212' in css


@pytest.mark.parametrize('source', SOURCES)
def test_installed_documentation_preserves_canonical_claims_and_executable_examples(source):
    inventory = json.loads((ROOT / 'chances/docs/sources.json').read_text())
    entries = {entry['source']: entry for entry in inventory['sources']}
    assert set(entries) == set(SOURCES)
    entry = entries[source]
    original = (ROOT / source).read_text()
    installed = (ROOT / 'chances' / entry['installed']).read_text()
    assert hashlib.sha256(original.encode()).hexdigest() == entry['source_sha256']
    assert hashlib.sha256(installed.encode()).hexdigest() == entry['installed_sha256']
    assert entry['route'] == next(
        document['slug'] for document in DOCS_MAP['documents'] if document['source'] == source
    )
    # Link transport may differ; code examples and claims must not be adapted.
    original_examples = re.findall(r'^```[^\n]*\n.*?^```[ \t]*$', original, flags=re.M | re.S)
    installed_examples = re.findall(r'^```[^\n]*\n.*?^```[ \t]*$', installed, flags=re.M | re.S)
    assert original_examples == installed_examples
    assert installed.startswith(
        f'<!-- Generated from {source}; edit the canonical repository source. -->'
    )
    for alias in entry.get('aliases', []):
        alias_content = (ROOT / 'chances' / alias['installed']).read_text()
        assert hashlib.sha256(alias_content.encode()).hexdigest() == alias['installed_sha256']
        assert (
            re.findall(r'^```[^\n]*\n.*?^```[ \t]*$', alias_content, flags=re.M | re.S)
            == original_examples
        )


@pytest.fixture(scope='session')
def documentation_artifacts(tmp_path_factory):
    """Build temporary artifacts once; prove the released package boundary."""
    destination = tmp_path_factory.mktemp('documentation-build')
    result = subprocess.run(
        [sys.executable, '-m', 'build', '--no-isolation', '--outdir', str(destination)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, 'SOURCE_DATE_EPOCH': '1704067200'},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheel = next(destination.glob('*.whl'))
    sdist = next(destination.glob('*.tar.gz'))
    with zipfile.ZipFile(wheel) as archive:
        wheel_files = {name: archive.read(name) for name in archive.namelist()}
        assert len(wheel_files) == len(archive.namelist()), (
            'Wheel must not contain duplicate destinations'
        )
    with tarfile.open(sdist) as archive:
        sdist_files = {
            PurePosixPath(member.name)
            .relative_to(member.name.split('/')[0])
            .as_posix(): archive.extractfile(member).read()
            for member in archive.getmembers()
            if member.isfile()
        }
    installed = destination / 'installed'
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(installed)
    return wheel_files, sdist_files, installed


def test_distribution_contains_every_reader_route_without_build_dependency_trees(
    documentation_artifacts,
):
    wheel, sdist, _ = documentation_artifacts
    inventory = json.loads(wheel['chances/docs/sources.json'])
    assert set(entry['source'] for entry in inventory['sources']) == set(SOURCES)
    for entry in inventory['sources']:
        installed_name = 'chances/' + entry['installed']
        assert installed_name in wheel
        assert hashlib.sha256(wheel[installed_name]).hexdigest() == entry['installed_sha256']
        assert entry['source'] in sdist
        assert hashlib.sha256(sdist[entry['source']]).hexdigest() == entry['source_sha256']
        for alias in entry.get('aliases', []):
            alias_name = 'chances/' + alias['installed']
            assert hashlib.sha256(wheel[alias_name]).hexdigest() == alias['installed_sha256']
    assert 'chances/README.md' not in wheel
    assert 'chances/docs/repository/chances/README.md' in wheel
    for source in (
        'docs-site/package.json',
        'docs-site/package-lock.json',
        'docs-site/docs-map.json',
        'docs-site/product-docs.json',
        'docs-site/scripts/assemble-docs.mjs',
        'docs-site/src/css/custom.css',
        'scripts/build_catalog.py',
        '.markdownlint.json',
    ):
        assert source in sdist, source
    forbidden_segments = {
        'node_modules',
        '.generated',
        '.docusaurus',
        'build',
        'test-results',
        'playwright-report',
    }
    assert not [
        name
        for name in sdist
        if name.startswith('docs-site/')
        and forbidden_segments.intersection(PurePosixPath(name).parts)
    ]


def test_every_installed_markdown_link_and_fragment_resolves_inside_the_wheel(
    documentation_artifacts,
):
    files, _, _ = documentation_artifacts
    markdown = {
        name: content.decode('utf-8') for name, content in files.items() if name.endswith('.md')
    }
    assert markdown
    for source, content in markdown.items():
        for link in _links(content):
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or link.startswith('/'):
                continue
            target = (
                posixpath.normpath(posixpath.join(posixpath.dirname(source), unquote(parsed.path)))
                if parsed.path
                else source
            )
            assert target in files, f'{source}: {link} -> missing {target}'
            if parsed.fragment and target in markdown:
                assert unquote(parsed.fragment) in _anchors(markdown[target]), (
                    f'{source}: unresolved {link}'
                )


@pytest.mark.parametrize('source', SOURCES)
def test_standalone_documentation_python_examples_run_from_the_built_wheel(
    source, documentation_artifacts, tmp_path
):
    _, _, installed = documentation_artifacts
    code_blocks = re.findall(
        r'^```python\n(.*?)\n```[ \t]*$', (ROOT / source).read_text(), flags=re.M | re.S
    )
    for index, code in enumerate(code_blocks):
        compile(code, f'{source}:python-example-{index + 1}', 'exec')
        # The first import must resolve to artifact bytes, not the checkout.
        program = f'import sys\nsys.path.insert(0, {str(installed)!r})\n' + code
        result = subprocess.run(
            [sys.executable, '-c', program],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, 'PYTHONPATH': str(installed)},
        )
        assert result.returncode == 0, (
            f'{source}:example-{index + 1}\n{result.stdout}{result.stderr}'
        )


def test_mirror_generation_rejects_missing_targets_and_repository_escape():
    generator = runpy.run_path(str(ROOT / 'scripts/build_catalog.py'))
    profile = json.loads((ROOT / 'docs-site/product-docs.json').read_text())
    installed = ROOT / 'chances/docs/README.md'
    for target in ('documentation-page-that-does-not-exist.md', '../../../../etc/passwd'):
        with pytest.raises(ValueError):
            generator['rewrite_link'](target, 'README.md', installed, {}, profile)


def test_legacy_manual_aliases_bind_to_their_canonical_reader_pages():
    inventory = json.loads((ROOT / 'chances/docs/sources.json').read_text())
    aliases = {
        alias['installed']: entry['source']
        for entry in inventory['sources']
        for alias in entry.get('aliases', [])
    }
    assert aliases == {
        'docs/recipes.md': 'docs/Reference/Specifications-and-Receipts.md',
        'docs/migration.md': 'docs/Guides/Migration.md',
    }


def test_source_and_wheel_are_byte_reproducible_for_the_declared_build_environment(
    documentation_artifacts,
):
    _, _, installed = documentation_artifacts
    first = installed.parent
    second = first / 'second-build'
    result = subprocess.run(
        [sys.executable, '-m', 'build', '--no-isolation', '--outdir', str(second)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, 'SOURCE_DATE_EPOCH': '1704067200'},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for suffix in ('*.whl', '*.tar.gz'):
        original = next(first.glob(suffix))
        rebuilt = second / original.name
        assert rebuilt.is_file()
        assert (
            hashlib.sha256(original.read_bytes()).digest()
            == hashlib.sha256(rebuilt.read_bytes()).digest()
        )


@pytest.fixture
def extracted_documentation_source(documentation_artifacts, tmp_path):
    """Use the actual built source archive, with its intentionally omitted enforcement."""
    _, files, _ = documentation_artifacts
    source = tmp_path / 'extracted'
    for relative, content in files.items():
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    assert (source / 'PKG-INFO').is_file()
    assert not (source / '.git').exists()
    assert not (source / 'CLAUDE.md').exists()
    return source


def _artifact_catalog(source, *, check):
    return subprocess.run(
        [sys.executable, 'scripts/build_catalog.py', *(['--check'] if check else [])],
        cwd=source,
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
    )


def test_clean_extracted_sdist_reproduces_catalog_and_manuals(extracted_documentation_source):
    source = extracted_documentation_source
    result = _artifact_catalog(source, check=True)
    assert result.returncode == 0, result.stdout + result.stderr
    result = _artifact_catalog(source, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    # Rewriting is byte-neutral in an unchanged source artifact.
    result = _artifact_catalog(source, check=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('mutation', [
    'source', 'profile', 'map', 'manifest', 'inventory', 'binding', 'mirror', 'alias',
    'missing_mirror', 'missing_alias', 'missing_metadata', 'forged_metadata', 'git_checkout',
])
def test_source_artifact_mode_rejects_mutation_before_writing(
    extracted_documentation_source, mutation
):
    source = extracted_documentation_source
    paths = {
        'source': 'docs/README.md',
        'profile': 'docs-site/product-docs.json',
        'map': 'docs-site/docs-map.json',
        'manifest': 'chances/docs/sources.json',
        'mirror': 'chances/docs/README.md',
        'alias': 'chances/docs/recipes.md',
    }
    if mutation in paths:
        path = source / paths[mutation]
        path.write_text(path.read_text() + '\n<!-- changed -->\n' if mutation in {'source', 'mirror', 'alias'}
                        else path.read_text() + '\n')
    elif mutation in {'inventory', 'binding'}:
        path = source / ('chances/docs/sources.json' if mutation == 'inventory' else 'chances/docs/contracts.json')
        data = json.loads(path.read_text())
        if mutation == 'inventory':
            data['repository_links']['forged-missing-file.md'] = 'blob'
        else:
            data['documentation_sources_sha256'] = '0' * 64
        path.write_text(json.dumps(data))
    elif mutation in {'missing_mirror', 'missing_alias'}:
        (source / ('chances/docs/README.md' if mutation == 'missing_mirror' else 'chances/docs/recipes.md')).unlink()
    elif mutation == 'missing_metadata':
        (source / 'PKG-INFO').unlink()
    elif mutation == 'forged_metadata':
        (source / 'PKG-INFO').write_text('Name: other-project\nVersion: 2.0.0\n')
    else:
        (source / '.git').mkdir()
    before = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in source.rglob('*') if path.is_file()}
    result = _artifact_catalog(source, check=False)
    assert result.returncode != 0, result.stdout + result.stderr
    assert 'ValueError' in result.stderr
    after = {path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in source.rglob('*') if path.is_file()}
    assert after == before
