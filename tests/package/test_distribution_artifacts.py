"""Shipped manuals and examples must agree with executable scientific contracts."""

import json
import re
import runpy
import subprocess
import sys
from pathlib import Path

import chances

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path(chances.__file__).parent


def test_shipped_agent_navigation_and_catalog_are_complete():
    for name in (
        'AGENTS.md',
        'docs/README.md',
        'docs/recipes.md',
        'docs/migration.md',
        'docs/research_batch.py',
        'docs/operations.json',
        'docs/contracts.json',
        'docs/sources.json',
    ):
        assert (PACKAGE / name).is_file(), name
    assert json.loads((PACKAGE / 'docs/operations.json').read_text()) == chances.catalog()
    contracts = json.loads((PACKAGE / 'docs/contracts.json').read_text())
    assert contracts['package_version'] == chances.__version__
    assert contracts['receipt']['version'] == 1
    assert contracts['randomness']['default_engine'] == 'pcg64dxsm'
    sources = json.loads((PACKAGE / 'docs/sources.json').read_text())
    assert sources['schema_version'] == 'chances.documentation-sources.v1'
    assert sources['entrypoint'] == 'docs/README.md'
    assert any(entry['source'] == 'README.md' for entry in sources['sources'])
    assert any(entry['source'] == 'chances/README.md' for entry in sources['sources'])


def test_readme_example_is_executable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    blocks = re.findall(r'```python\n(.*?)\n```', (ROOT / 'README.md').read_text(), re.S)
    assert blocks
    for block in blocks:
        exec(compile(block, 'README.md', 'exec'), {})


def test_shipped_research_batch_saves_verified_replayable_evidence(tmp_path):
    namespace = runpy.run_path(str(PACKAGE / 'docs/research_batch.py'))
    result = namespace['run'](tmp_path / 'research-batch')
    saved = json.loads((tmp_path / 'research-batch/receipt.json').read_text())
    assert saved == result.receipt
    assert saved['output']['shape'] == [100]
    assert saved['randomness']['stream'] == 'experiment/replicate-1'
    contract = json.loads((PACKAGE / 'docs/contracts.json').read_text())
    assert sorted(saved['checks']) == sorted(contract['receipt']['checks'])
    assert sorted(saved) == sorted(contract['receipt']['fields'])
    assert saved['contract']['shape'] == [100]


def test_generated_manuals_are_current():
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/build_catalog.py'), '--check'],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
