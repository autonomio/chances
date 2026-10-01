"""An executable, offline research batch with retained evidence and exact replay."""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import chances


def run(output: str | Path) -> chances.Generated:
    spec = {
        'version': 1,
        'operation': 'normal',
        'parameters': {'size': 100, 'loc': 0.0, 'scale': 1.0},
        'randomness': {'seed': 42, 'stream': 'experiment/replicate-1'},
    }
    chances.inspect(spec)
    first = chances.generate(spec)
    other_spec = deepcopy(spec)
    other_spec['randomness']['stream'] = 'experiment/replicate-2'
    other = chances.generate(other_spec)
    repeated = chances.generate(spec)
    assert first.data.shape == (100,)
    assert np.isfinite(first.data).all()
    assert np.array_equal(first.data, repeated.data)
    assert first.receipt == repeated.receipt
    assert not np.array_equal(first.data, other.data)
    # Running unrelated streams first does not advance this replicate.
    assert np.array_equal(other.data, chances.generate(other_spec).data)
    first.write(output)
    checked = chances.verify(output)
    replayed = chances.replay(output)
    assert np.array_equal(first.data, checked.data)
    assert np.array_equal(first.data, replayed.data)
    assert first.receipt == checked.receipt == replayed.receipt
    assert (Path(output) / 'data.npy').is_file()
    assert (Path(output) / 'recipe.json').is_file()
    assert (Path(output) / 'receipt.json').is_file()
    try:
        first.write(output)
    except chances.ChancesError as error:
        assert error.code == 'OUTPUT_EXISTS'
    else:
        raise AssertionError('An existing result directory was overwritten.')
    return first


if __name__ == '__main__':
    with TemporaryDirectory(prefix='chances-example-') as directory:
        result = run(Path(directory) / 'batch')
        sys.stdout.write(f'Verified: {result.data.size} values, named streams, identical replay.\n')
