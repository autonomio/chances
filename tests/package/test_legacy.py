"""The deprecated facade must not retain unsafe legacy failure modes."""

import random

import numpy as np
import pytest

import chances


def old(maximum=16, n=8):
    with pytest.warns(DeprecationWarning):
        return chances.Randomizer(maximum, n, seed=31)


@pytest.mark.parametrize(
    'method',
    [
        'uniform_mersenne',
        'latin_matrix',
        'latin_sudoku',
        'latin_improved',
        'sobol',
        'halton',
        'korobov_matrix',
    ],
)
def test_legacy_index_facade_repeats_and_preserves_global_state(method):
    r = old()
    python_before, numpy_before = random.getstate(), np.random.get_state()
    first = getattr(r, method)()
    assert first == getattr(r, method)()
    assert len(first) == 8
    assert len(set(first)) == 8
    assert all(0 <= value < 16 for value in first)
    assert random.getstate() == python_before
    assert all(np.array_equal(a, b) for a, b in zip(np.random.get_state(), numpy_before))


def test_impossible_crypto_request_fails_at_construction():
    with pytest.warns(DeprecationWarning), pytest.raises(chances.ChancesError):
        chances.Randomizer(3, 4)


def test_crypto_draws_have_exact_size_support_and_uniqueness():
    values = old().uniform_crypto()
    assert len(values) == 8 and len(set(values)) == 8
    assert all(0 <= value < 16 for value in values)


@pytest.mark.parametrize('provider', ['quantum', 'ambience'])
def test_removed_network_providers_fail_explicitly(provider):
    with pytest.raises(chances.ChancesError) as error:
        getattr(old(), provider)()
    assert error.value.code == 'ENTROPY_PROVIDER_UNAVAILABLE'


def test_sudoku_impossible_geometry_is_rejected():
    with pytest.raises(chances.ChancesError):
        old(10, 10).latin_sudoku(dims=2, sudoku_boxes=2)


def test_legacy_alphabet_is_explicitly_seeded():
    with pytest.warns(DeprecationWarning):
        first = chances.generate_random_alpha(30, seed=17)
    with pytest.warns(DeprecationWarning):
        second = chances.generate_random_alpha(30, dtype=list, seed=17)
    assert first == ''.join(second)
    assert len(first) == 30
