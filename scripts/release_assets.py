"""Archive complete tracked release source and publish assets without replacement."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
import tempfile
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]


def command(*args: str) -> bytes:
    """Run release tooling with visible, fatal errors and bounded execution."""
    return subprocess.run(args, cwd=ROOT, check=True, stdout=subprocess.PIPE,
                          timeout=120).stdout


def archive(output: Path) -> None:
    """Write deterministic source, refusing export exclusions and checkout writes."""
    if output.resolve().is_relative_to(ROOT):
        raise ValueError('Source archive must be outside the release checkout.')
    version = tomllib.loads(command('git', 'show', 'HEAD:pyproject.toml').decode())['project']['version']
    prefix = f'chances-{version}/'
    payload = command('git', 'archive', '--format=tar', f'--prefix={prefix}', 'HEAD')
    tracked = command('git', 'ls-tree', '-rz', '--name-only', 'HEAD').decode().split('\0')
    with tarfile.open(fileobj=io.BytesIO(payload)) as source:
        included = {member.name for member in source if not member.isdir()}
    if included != {prefix + name for name in tracked if name}:
        raise ValueError('Source archive does not contain every tracked file; exclusions or submodules are unsupported.')
    with output.open('wb') as target, gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as compressed:
        compressed.write(payload)
    print(f'{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}')


def upload(tag: str, assets: list[Path]) -> None:
    """Keep existing identical assets and refuse any attempt to replace bytes."""
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise ValueError('Release tag must be vMAJOR.MINOR.PATCH.')
    if not assets or len({asset.name for asset in assets}) != len(assets):
        raise ValueError('Release assets must have unique filenames.')
    for asset in assets:
        if not asset.is_file() or asset.is_symlink():
            raise ValueError(f'Release asset is not a regular file: {asset}')
    release = json.loads(command('gh', 'release', 'view', tag, '--json', 'assets'))
    existing = {asset['name'] for asset in release['assets']}
    pending = []
    with tempfile.TemporaryDirectory(prefix='chances-release-assets-') as directory:
        for asset in assets:
            if asset.name in existing:
                command('gh', 'release', 'download', tag, '--pattern', asset.name, '--dir', directory)
                downloaded = Path(directory) / asset.name
                if downloaded.read_bytes() != asset.read_bytes():
                    raise ValueError(f'Immutable release asset differs: {asset.name}')
                print(f'Already published identical asset: {asset.name}')
            else:
                pending.append(str(asset.resolve()))
        if pending:
            command('gh', 'release', 'upload', tag, *pending)
            print(f'Published {len(pending)} immutable release asset(s).')


def main() -> None:
    """Dispatch the release-only archive and immutable-upload operations."""
    parser = argparse.ArgumentParser(description=__doc__)
    operations = parser.add_subparsers(dest='operation', required=True)
    source = operations.add_parser('archive')
    source.add_argument('--output', type=Path, required=True)
    publication = operations.add_parser('upload')
    publication.add_argument('--tag', required=True)
    publication.add_argument('--assets', type=Path, nargs='+', required=True)
    arguments = parser.parse_args()
    if arguments.operation == 'archive':
        archive(arguments.output)
    else:
        upload(arguments.tag, arguments.assets)


if __name__ == '__main__':
    main()
