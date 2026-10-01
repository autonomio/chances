"""Put `governance/` on `sys.path` so gate modules and tests can import the
shared `_common` helper by bare name — the same way the gates resolve it when
run as scripts (`python governance/check_*.py`), where `governance/` is the
script directory. Gates that are imported as `governance.<name>` in tests rely
on this too, since their internal `import _common` resolves against this path.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

_GOVERNANCE = Path(__file__).resolve().parents[1]
if str(_GOVERNANCE) not in sys.path:
    sys.path.insert(0, str(_GOVERNANCE))


@pytest.fixture
def seed_repository(tmp_path: Path) -> Path:
    """A bounded template fixture proves rename behavior without copying Chances."""
    root = Path(__file__).resolve().parents[2]
    repo = tmp_path / 'seed'
    (repo / 'governance').mkdir(parents=True)
    for source in (root / 'governance').glob('*.py'):
        shutil.copy2(source, repo / 'governance' / source.name)
    seed = 'new' + '_repository_' + 'template'
    (repo / seed).mkdir()
    (repo / seed / '__init__.py').write_text(
        '\"\"\"Public package surface for the seed.\"\"\"\n\n__all__: list[str] = []\n'
    )
    (repo / 'pyproject.toml').write_text(
        '[project]\nname = "new-repository-template"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["new_repository_template"]\n'
        '[tool.pyright]\ninclude = ["new_repository_template"]\n'
    )
    config = yaml.safe_load((root / 'governance.yml').read_text())
    config['repository']['name'] = 'new-repository-template'
    config['layout']['package_root'] = seed
    config['layout']['coverage_source'] = seed
    (repo / 'governance.yml').write_text(yaml.safe_dump(config))
    (repo / '.github').mkdir()
    (repo / '.github/budgets.json').write_text(json.dumps({'modules': {}}))
    (repo / 'README.md').write_text(
        '# {DISPLAY_NAME}\n{ONE_SENTENCE_DESCRIPTION}\n'
        'https://github.com/Autonomio/new-repository-template\n'
    )
    (repo / 'SETUP.md').write_text('--template Autonomio/new-repository-template\n')
    (repo / 'CITATION.cff').write_text('title: "{DISPLAY_NAME}"\n')
    (repo / 'docs-site').mkdir()
    profile = {
        'productId': '{REPOSITORY_NAME}', 'productName': '{DISPLAY_NAME}',
        'tagline': '{ONE_SENTENCE_DESCRIPTION}', 'siteUrl': 'https://autonomio.github.io',
        'basePath': '/{REPOSITORY_NAME}/',
        'sourceRepoUrl': 'https://github.com/{REPOSITORY_OWNER}/{REPOSITORY_NAME}',
        'sourceBranch': 'master',
    }
    (repo / 'docs-site/product-docs.json').write_text(json.dumps(profile))
    return repo
