"""Product runtime evidence is real, opt-in and independent of governance imports."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_profile_records_all_tests_and_real_wall_time(tmp_path: Path) -> None:
    shutil.copy2(REPO_ROOT / 'tests/package/conftest.py', tmp_path / 'conftest.py')
    (tmp_path / 'test_fixture.py').write_text('def test_one():\n    assert 1 + 1 == 2\n')
    profile = tmp_path / 'runtime/profile.json'
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q'], cwd=tmp_path, check=False,
        capture_output=True, text=True, env={**os.environ, 'TEST_RUNTIME_PROFILE': str(profile)},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    evidence = json.loads(profile.read_text())
    assert evidence['total_seconds'] > 0
    assert len(evidence['tests']) == 1
    assert evidence['tests'][0]['name'] == 'test_fixture.py::test_one'
    assert 0 <= evidence['tests'][0]['duration'] <= evidence['total_seconds']
    assert 'governance' not in (tmp_path / 'conftest.py').read_text().split('from __future__')[1]
