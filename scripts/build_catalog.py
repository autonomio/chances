#!/usr/bin/env python3
"""Generate installed navigation/contracts from the live operation registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from email.parser import Parser
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def pretty(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n'


def outputs() -> dict[Path, str]:
    from chances import __version__
    from chances._api import DEFAULT_LIMITS, MAX_JSON_BYTES, RECEIPT_VERSION, SPEC_VERSION
    from chances._operations import catalog
    from chances._random import DERIVATION, ENGINES

    registry = catalog()
    contracts = {
        'schema_version': 'chances.contracts.v1',
        'package_version': __version__,
        'capabilities': {
            'operations': len(registry['operations']),
            'distributions': len(registry['distributions']),
        },
        'navigation': {
            'paths_relative_to': 'Path(chances.__file__).parent',
            'entrypoint': 'AGENTS.md',
            'documentation_hub': 'docs/repository/docs/README.md',
            'documentation_sources': 'docs/sources.json',
            'package_boundary': 'docs/repository/chances/README.md',
            'specifications': 'docs/recipes.md',
            'operations': 'docs/operations.json',
            'migration': 'docs/migration.md',
            'executable_workflow': 'docs/research_batch.py',
        },
        'specification': {
            'version': SPEC_VERSION,
            'fields': ['version', 'operation', 'parameters', 'randomness', 'limits'],
            'required': ['operation', 'randomness.seed'],
            'maximum_json_bytes': MAX_JSON_BYTES,
            'default_limits': DEFAULT_LIMITS,
            'limit_range': 'positive integers less than 2**63',
        },
        'randomness': {
            'default_engine': 'pcg64dxsm',
            'engines': {name: engine.__name__ for name, engine in ENGINES.items()},
            'derivation': DERIVATION,
            'seed_range': 'integer in [0, 2**256); booleans rejected',
            'stream': {'default': 'default', 'normalization': 'NFC', 'maximum_utf8_bytes': 512},
            'global_rng_mutation': False,
            'shared_stream_state': False,
        },
        'array': {
            'dtype_kinds': ['b', 'i', 'u', 'f', 'U', 'S'],
            'maximum_dimensions': 16,
            'finite_floats_required': True,
            'pickle': False,
            'hash_contract': 'SHA256(chances-array-v1 NUL + canonical JSON(dtype.str,shape) + NUL + C-order bytes)',
            'identity_fields': ['dtype', 'shape', 'values', 'bytes', 'sha256'],
        },
        'receipt': {
            'version': RECEIPT_VERSION,
            'fields': [
                'receipt_version',
                'versions',
                'environment',
                'spec',
                'spec_sha256',
                'source',
                'randomness',
                'checks',
                'contract',
                'output',
                'receipt_sha256',
            ],
            'rng_fields': ['seed', 'stream', 'engine', 'derivation', 'state_before', 'state_after'],
            'rng_state': 'Bit-generator state plus SeedSequence entropy, spawn_key, pool_size, and n_children_spawned; captures QMC child spawning.',
            'hash_contract': 'SHA256 of sorted, compact, finite UTF-8 JSON, excluding receipt_sha256 itself',
            'checks': [
                'finite',
                'supported_dtype',
                'resource_limits',
                'shape',
                'dtype',
                'declared_support',
                'structural_constraints',
            ],
            'contract': {
                'required_fields': ['shape', 'dtype', 'finite', 'support'],
                'optional_fields': ['dependence', 'stratification'],
            },
            'timestamps': False,
            'signed': False,
            'bundle_files': ['data.npy', 'recipe.json', 'receipt.json'],
            'optional_source_file': 'source.npy',
            'verification': 'Check archive integrity and declared contracts without regenerating values.',
            'replay': 'Verify archive, reject mismatched versions/environment, regenerate and compare evidence/output.',
        },
    }
    documentation = documentation_outputs()
    contracts['documentation_sources_sha256'] = sha256(
        documentation[ROOT / 'chances/docs/sources.json']
    )
    generated = {
        ROOT / 'chances/docs/operations.json': pretty(registry),
        ROOT / 'chances/docs/contracts.json': pretty(contracts),
    }
    generated.update(documentation)
    return generated


def sha256(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def repository_file(source: str) -> Path:
    path = (ROOT / source).resolve()
    if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
        raise ValueError(f'Documentation source must be an existing repository file: {source}')
    return path


def installed_location(source: str) -> Path:
    if source == 'README.md':
        return ROOT / 'chances/docs/README.md'
    return ROOT / 'chances/docs/repository' / source


def rewrite_link(
    target: str, source: str, installed: Path, locations: dict[str, Path], profile: dict,
    repository_targets: dict[str, str] | None = None,
    artifact_targets: dict[str, str] | None = None,
) -> str:
    match = re.fullmatch(r'<?([^\s>]+)>?(.*)', target.strip())
    if match is None:
        raise ValueError(f'Unsupported Markdown link target in {source}: {target}')
    url, suffix = match.groups()
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or url.startswith(('#', '/')):
        return target
    resolved = (ROOT / PurePosixPath(source).parent / unquote(parsed.path)).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f'Documentation link leaves the repository in {source}: {url}')
    if resolved.is_dir() and (resolved / 'README.md').is_file():
        resolved = resolved / 'README.md'
    relative_source = resolved.relative_to(ROOT).as_posix()
    destination = locations.get(relative_source)
    archived_kind = (artifact_targets or {}).get(relative_source)
    if destination is None and not resolved.exists() and archived_kind is None:
        raise ValueError(f'Documentation link target is missing in {source}: {url}')
    if destination is None and relative_source.startswith('chances/'):
        if not resolved.exists():
            raise ValueError(f'Installed package link target is missing: {relative_source}')
        # Existing package artifacts (JSON catalogs, code, agent entrypoint)
        # remain local even when they are not website Markdown pages.
        destination = resolved
    if destination is not None:
        rewritten = Path(os.path.relpath(destination, installed.parent)).as_posix()
        rewritten = quote(rewritten, safe='/-._~')
    else:
        kind = ('tree' if resolved.is_dir() else 'blob') if resolved.exists() else archived_kind
        if repository_targets is not None:
            repository_targets[relative_source] = kind
        rewritten = f'{profile["sourceRepoUrl"].rstrip("/")}/{kind}/{profile["sourceBranch"]}/{quote(relative_source, safe="/-._~")}'
    if parsed.query:
        rewritten += '?' + parsed.query
    if parsed.fragment:
        rewritten += '#' + parsed.fragment
    return rewritten + suffix


def rewrite_markdown(
    content: str, source: str, installed: Path, locations: dict[str, Path], profile: dict,
    repository_targets: dict[str, str] | None = None,
    artifact_targets: dict[str, str] | None = None,
) -> str:
    # Fenced examples are executable source and must never be rewritten.
    chunks = re.split(r'(^```[^\n]*\n.*?^```[ \t]*$)', content, flags=re.M | re.S)
    for index in range(0, len(chunks), 2):
        prose = chunks[index]
        prose = re.sub(
            r'(\[[^\]\n]*\]\()([^\n)]+)(\))',
            lambda match: (
                match[1] + rewrite_link(match[2], source, installed, locations, profile, repository_targets, artifact_targets) + match[3]
            ),
            prose,
        )
        prose = re.sub(
            r'^(\[[^\]\n]+\]:[ \t]*)([^\n]+)$',
            lambda match: match[1] + rewrite_link(match[2], source, installed, locations, profile, repository_targets, artifact_targets),
            prose,
            flags=re.M,
        )
        prose = re.sub(
            r"(<(?:a|img)\b[^>]*?\b(?:href|src)=[\"'])([^\"']+)([\"'])",
            lambda match: (
                match[1] + rewrite_link(match[2], source, installed, locations, profile, repository_targets, artifact_targets) + match[3]
            ),
            prose,
            flags=re.I,
        )
        chunks[index] = prose
    return ''.join(chunks)


def artifact_repository_targets(profile_text: str, map_text: str, sources: list[str]) -> dict[str, str]:
    """Reuse omitted repository links only from an unchanged, bound source artifact."""
    if (ROOT / '.git').exists() or not (ROOT / 'PKG-INFO').is_file():
        return {}
    from chances import __version__

    metadata = Parser().parsestr((ROOT / 'PKG-INFO').read_text(encoding='utf-8'))
    if metadata.get_all('Name') != ['chances'] or metadata.get_all('Version') != [__version__]:
        raise ValueError('Source artifact PKG-INFO identity does not match Chances')
    manifest_text = (ROOT / 'chances/docs/sources.json').read_text(encoding='utf-8')
    manifest = json.loads(manifest_text)
    contracts = json.loads((ROOT / 'chances/docs/contracts.json').read_text(encoding='utf-8'))
    if contracts.get('documentation_sources_sha256') != sha256(manifest_text):
        raise ValueError('Source artifact documentation manifest binding does not match')
    if (manifest.get('profile_sha256') != sha256(profile_text)
            or manifest.get('map_sha256') != sha256(map_text)):
        raise ValueError('Source artifact documentation profile or map changed; regenerate in Git checkout')
    entries = {entry['source']: entry for entry in manifest['sources']}
    if set(entries) != set(sources) or len(entries) != len(manifest['sources']):
        raise ValueError('Source artifact documentation inventory does not match the source map')
    for source, entry in entries.items():
        if entry['source_sha256'] != sha256(repository_file(source).read_text(encoding='utf-8')):
            raise ValueError(f'Source artifact documentation changed: {source}; regenerate in Git checkout')
        for mirror in [entry, *entry.get('aliases', [])]:
            installed = (ROOT / 'chances' / mirror['installed']).resolve()
            if (not installed.is_relative_to((ROOT / 'chances').resolve())
                    or not installed.is_file()
                    or mirror['installed_sha256'] != sha256(installed.read_text(encoding='utf-8'))):
                raise ValueError(f'Source artifact installed manual changed or missing: {mirror["installed"]}')
    targets = manifest.get('repository_links')
    if not isinstance(targets, dict):
        raise ValueError('Source artifact has no checkout-validated repository link inventory')
    for target, kind in targets.items():
        path = PurePosixPath(target)
        if path.is_absolute() or '..' in path.parts or kind not in {'blob', 'tree'}:
            raise ValueError('Source artifact repository link inventory is malformed')
    return targets


def documentation_outputs() -> dict[Path, str]:
    profile_text = (ROOT / 'docs-site/product-docs.json').read_text(encoding='utf-8')
    map_text = (ROOT / 'docs-site/docs-map.json').read_text(encoding='utf-8')
    profile = json.loads(profile_text)
    docs_map = json.loads(map_text)
    if not isinstance(profile.get('sourceBranch'), str) or not profile['sourceBranch']:
        raise ValueError('Documentation profile must declare its source branch')
    documents = docs_map['documents']
    sources = [document['source'] for document in documents]
    if 'README.md' not in sources or len(sources) != len(set(sources)):
        raise ValueError(
            'Maintained docs must map the canonical README once and have unique sources'
        )
    if 'chances/docs/README.md' in sources:
        raise ValueError('The installed README is generated; map canonical README.md instead')
    artifact_targets = artifact_repository_targets(profile_text, map_text, sources)
    repository_targets: dict[str, str] = {}
    locations = {source: installed_location(source) for source in sources}
    locations['chances/docs/README.md'] = ROOT / 'chances/docs/README.md'
    aliases = {
        'chances/docs/recipes.md': 'docs/Reference/Specifications-and-Receipts.md',
        'chances/docs/migration.md': 'docs/Guides/Migration.md',
    }
    if not set(aliases.values()).issubset(sources):
        raise ValueError('The source map must include canonical specification and migration pages')
    locations.update({alias: ROOT / alias for alias in aliases})
    generated: dict[Path, str] = {}
    inventory = []
    for document in documents:
        source = document['source']
        original = repository_file(source).read_text(encoding='utf-8')
        installed = locations[source]
        notice = f'<!-- Generated from {source}; edit the canonical repository source. -->\n\n'
        rendered = notice + rewrite_markdown(original, source, installed, locations, profile, repository_targets, artifact_targets)
        generated[installed] = rendered
        inventory.append(
            {
                'source': source,
                'source_sha256': sha256(original),
                'installed': installed.relative_to(ROOT / 'chances').as_posix(),
                'installed_sha256': sha256(rendered),
                'route': document['slug'],
            }
        )
    by_source = {entry['source']: entry for entry in inventory}
    for alias, source in aliases.items():
        original = repository_file(source).read_text(encoding='utf-8')
        installed = ROOT / alias
        notice = f'<!-- Generated from {source}; edit the canonical repository source. -->\n\n'
        rendered = notice + rewrite_markdown(original, source, installed, locations, profile, repository_targets, artifact_targets)
        generated[installed] = rendered
        by_source[source].setdefault('aliases', []).append(
            {
                'installed': installed.relative_to(ROOT / 'chances').as_posix(),
                'installed_sha256': sha256(rendered),
            }
        )
    generated[ROOT / 'chances/docs/sources.json'] = pretty(
        {
            'schema_version': 'chances.documentation-sources.v1',
            'source_repo_url': profile['sourceRepoUrl'],
            'source_branch': profile['sourceBranch'],
            'profile_sha256': sha256(profile_text),
            'map_sha256': sha256(map_text),
            'repository_links': repository_targets,
            'entrypoint': 'docs/README.md',
            'sources': inventory,
            'ownership': 'Maintain each source once at its mapped repository path. Installed Markdown mirrors and legacy recipes.md/migration.md aliases are generated by scripts/build_catalog.py; never edit their copies.',
        }
    )
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--check',
        action='store_true',
        help='Reject stale shipped documentation without changing it.',
    )
    args = parser.parse_args()
    stale = []
    generated = outputs()
    mirror_root = ROOT / 'chances/docs/repository'
    orphaned = sorted(path for path in mirror_root.rglob('*.md') if path not in generated)
    for path in orphaned:
        if args.check:
            stale.append(str(path.relative_to(ROOT)))
        else:
            path.unlink()
    for path, content in generated.items():
        if args.check:
            if not path.is_file() or path.read_text(encoding='utf-8') != content:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
    if stale:
        print('Stale generated documentation: ' + ', '.join(stale), file=sys.stderr)
        return 1
    print(
        'Verified generated catalogs, contracts, and installed documentation mirrors.'
        if args.check
        else 'Generated catalogs, contracts, and installed documentation mirrors.'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
