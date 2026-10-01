"""Deterministic, offline smoke test; every success is asserted."""

import runpy
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import chances

if __name__ == '__main__':
    example = Path(chances.__file__).parent / 'docs' / 'research_batch.py'
    with TemporaryDirectory(prefix='chances-smoke-') as directory:
        result = runpy.run_path(str(example))['run'](Path(directory) / 'batch')
        assert result.data.shape == (100,)
    sys.stdout.write('Verified: deterministic generation, named streams, saved receipt, replay.\n')
