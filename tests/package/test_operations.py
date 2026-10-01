"""Scientific invariants for local, declared random operations."""

import random
from collections import Counter

import numpy as np
import pytest

import chances
from chances._errors import ChancesError


def protocol(operation, parameters, *, stream='research', seed=2026, engine='pcg64dxsm'):
    return {
        'version': 1,
        'operation': operation,
        'parameters': parameters,
        'randomness': {'seed': seed, 'stream': stream, 'engine': engine},
    }


def draw(operation, parameters, *, source=None, **randomness):
    return chances.generate(protocol(operation, parameters, **randomness), source=source).data


def assert_indices(values, n):
    assert np.issubdtype(values.dtype, np.integer)
    assert np.all(values >= 0)
    assert np.all(values < n)


def test_integers_honor_shape_half_open_bounds_and_dtype():
    values = draw('integers', {'low': -3, 'high': 7, 'size': [12, 5], 'dtype': 'int32'})
    assert values.shape == (12, 5)
    assert values.dtype == np.dtype('int32')
    assert np.all((-3 <= values) & (values < 7))


def test_inclusive_integer_endpoint_degenerate_interval():
    values = draw('integers', {'low': 7, 'high': 7, 'endpoint': True, 'size': 20})
    np.testing.assert_array_equal(values, np.full(20, 7))


def test_uniform_honors_bounds_and_zero_variance_normal_honors_location():
    uniform = draw('uniform', {'low': -4, 'high': -2, 'size': [5, 7]})
    assert uniform.shape == (5, 7)
    assert np.all((-4 <= uniform) & (uniform < -2))
    normal = draw('normal', {'loc': 3.5, 'scale': 0, 'size': [4, 6]})
    np.testing.assert_array_equal(normal, np.full((4, 6), 3.5))


def test_choice_without_replacement_preserves_uniqueness():
    selected = draw('choice', {'n': 20, 'size': 20, 'replace': False})
    np.testing.assert_array_equal(np.sort(selected), np.arange(20))


def test_choice_never_selects_zero_probability_outcomes():
    selected = draw('choice', {'n': 4, 'size': 100, 'p': [0, 0, 1, 0]})
    np.testing.assert_array_equal(selected, np.full(100, 2))


@pytest.mark.parametrize('operation', ['permutation', 'shuffle'])
def test_permutation_and_shuffle_preserve_population(operation):
    selected = draw(operation, {'n': 31})
    assert selected.shape == (31,)
    np.testing.assert_array_equal(np.sort(selected), np.arange(31))


def test_bootstrap_outputs_resample_indices_with_declared_shape():
    selected = draw('bootstrap', {'n': 17, 'resamples': 8, 'sample_size': 23})
    assert selected.shape == (8, 23)
    assert_indices(selected, 17)


def test_circular_block_bootstrap_preserves_within_block_adjacency():
    selected = draw(
        'bootstrap',
        {'n': 10, 'resamples': 6, 'sample_size': 12, 'mode': 'block', 'block_length': 3},
    )
    assert selected.shape == (6, 12)
    assert_indices(selected, 10)
    blocks = selected.reshape(6, 4, 3)
    np.testing.assert_array_equal(blocks[:, :, 1:], (blocks[:, :, :-1] + 1) % 10)


def test_cluster_bootstrap_selects_whole_clusters():
    selected = draw(
        'bootstrap',
        {
            'n': 8,
            'resamples': 12,
            'sample_size': 8,
            'mode': 'cluster',
            'groups': [0, 0, 1, 1, 2, 2, 3, 3],
        },
    )
    assert selected.shape == (12, 8)
    assert_indices(selected, 8)
    for resample in selected:
        counts = np.bincount(resample, minlength=8)
        np.testing.assert_array_equal(counts[::2], counts[1::2])


def test_allocation_retains_exact_requested_group_sizes():
    labels = draw(
        'balanced_allocation', {'counts': [7, 5, 3], 'labels': ['control', 'low', 'high']}
    )
    assert labels.shape == (15,)
    assert Counter(labels.tolist()) == {'control': 7, 'low': 5, 'high': 3}


def test_split_partitions_cover_every_observation_exactly_once():
    split = draw('split', {'n': 13, 'counts': [8, 3, 2]})
    assert split.shape == (13,)
    np.testing.assert_array_equal(np.sort(split), np.arange(13))
    train, validation, test = np.split(split, [8, 11])
    assert (len(train), len(validation), len(test)) == (8, 3, 2)
    assert set(train).isdisjoint(validation)
    assert set(train).isdisjoint(test)
    assert set(validation).isdisjoint(test)


@pytest.mark.parametrize('operation', ['sobol', 'halton', 'latin_hypercube'])
def test_designs_retain_multidimensional_coordinates(operation):
    points = draw(operation, {'n': 32, 'd': 4})
    assert points.shape == (32, 4)
    assert np.all(np.isfinite(points))
    assert np.all((0 <= points) & (points < 1))


@pytest.mark.parametrize('operation', ['sobol', 'latin_hypercube'])
def test_balanced_designs_have_one_point_per_axis_stratum(operation):
    points = draw(operation, {'n': 32, 'd': 4})
    for axis in points.T:
        np.testing.assert_array_equal(np.sort(np.floor(32 * axis).astype(int)), np.arange(32))


def test_korobov_coprime_generator_produces_latin_projections():
    points = draw('korobov', {'n': 11, 'd': 4, 'generator': 3})
    assert points.shape == (11, 4)
    assert np.all((0 <= points) & (points < 1))
    for axis in points.T:
        np.testing.assert_array_equal(np.sort(np.rint(11 * axis).astype(int)), np.arange(11))


@pytest.mark.parametrize(
    'operation,parameters',
    [
        ('integers', {'low': 4, 'high': 4}),
        ('integers', {'high': 10, 'size': -1}),
        ('integers', {'high': True}),
        ('integers', {'high': 10, 'dtype': 'float64'}),
        ('normal', {'scale': -1}),
        ('normal', {'loc': float('nan')}),
        ('uniform', {'high': float('inf')}),
        ('choice', {'n': 5, 'size': 6, 'replace': False}),
        ('choice', {'n': 3, 'p': [0.5, 0.5]}),
        ('choice', {'n': 3, 'p': [0.5, -0.5, 1]}),
        ('choice', {'n': 3, 'p': [0.2, 0.2, 0.2]}),
        ('balanced_allocation', {'counts': [2, -1]}),
        ('balanced_allocation', {'counts': [2, 1], 'labels': ['only']}),
        ('split', {'n': 13, 'counts': [8, 3, 1]}),
        ('sobol', {'n': 31, 'd': 2}),
        ('latin_hypercube', {'n': 10, 'd': 0}),
        ('korobov', {'n': 10, 'd': 2, 'generator': 4}),
        ('sudoku', {'n': 10, 'd': 2, 'boxes': 2}),
        ('bootstrap', {'n': 5, 'mode': 'block', 'block_length': 0}),
        ('bootstrap', {'n': 5, 'mode': 'cluster', 'groups': [0, 0, 1, 1, 1]}),
    ],
)
def test_invalid_scientific_parameters_fail_before_generation(operation, parameters):
    with pytest.raises(ChancesError):
        chances.inspect(protocol(operation, parameters))


def test_named_streams_are_repeatable_and_independent_of_call_order():
    specs = [
        protocol('normal', {'size': [16, 3]}, stream=name)
        for name in ('experiment-a', 'experiment-b', 'experiment-c')
    ]
    forward = {spec['randomness']['stream']: chances.generate(spec).data for spec in specs}
    reverse = {
        spec['randomness']['stream']: chances.generate(spec).data for spec in reversed(specs)
    }
    for name in forward:
        np.testing.assert_array_equal(forward[name], reverse[name])
    assert not np.array_equal(forward['experiment-a'], forward['experiment-b'])


@pytest.mark.parametrize('engine', ['pcg64dxsm', 'pcg64', 'philox', 'sfc64', 'mt19937'])
def test_declared_engines_are_repeatable(engine):
    first = draw('normal', {'size': 32}, engine=engine)
    second = draw('normal', {'size': 32}, engine=engine)
    np.testing.assert_array_equal(first, second)


def test_generation_preserves_python_and_numpy_global_rng_states():
    python_before = random.getstate()
    numpy_before = np.random.get_state()
    draw('normal', {'size': [8, 3]})
    draw('latin_hypercube', {'n': 16, 'd': 3})
    assert random.getstate() == python_before
    numpy_after = np.random.get_state()
    assert numpy_before[0] == numpy_after[0]
    np.testing.assert_array_equal(numpy_before[1], numpy_after[1])
    assert numpy_before[2:] == numpy_after[2:]


def test_unrelated_global_rng_draws_do_not_change_declared_stream():
    python_state, numpy_state = random.getstate(), np.random.get_state()
    try:
        first = draw('normal', {'size': 40})
        random.random()
        np.random.random(37)
        second = draw('normal', {'size': 40})
        np.testing.assert_array_equal(first, second)
    finally:
        random.setstate(python_state)
        np.random.set_state(numpy_state)


def test_sudoku_preserves_latin_strata_and_every_coarse_cell():
    points = draw('sudoku', {'n': 24, 'd': 3, 'boxes': 2})
    assert points.shape == (24, 3)
    assert np.all((0 <= points) & (points < 1))
    for axis in points.T:
        np.testing.assert_array_equal(np.sort(np.floor(24 * axis).astype(int)), np.arange(24))
    cells = np.floor(points * 2).astype(int)
    counts = Counter(map(tuple, cells.tolist()))
    assert len(counts) == 8
    assert set(counts.values()) == {3}


def test_poisson_disk_honors_exact_count_and_minimum_separation():
    points = draw('poisson_disk', {'n': 15, 'd': 2, 'radius': 0.12, 'max_trials': 2000})
    assert points.shape == (15, 2)
    assert np.all((0 <= points) & (points < 1))
    distances = np.sqrt(np.sum((points[:, None, :] - points[None, :, :]) ** 2, axis=-1))
    assert np.min(distances[np.triu_indices(15, k=1)]) >= 0.12


def test_impossible_poisson_disk_sampling_fails_without_partial_output():
    with pytest.raises(ChancesError):
        draw('poisson_disk', {'n': 2, 'd': 1, 'radius': 1.1, 'max_trials': 20})


@pytest.mark.parametrize('operation', ['permutation', 'shuffle'])
def test_source_operations_preserve_complete_observation_rows(operation):
    source = np.array([[10, 100], [20, 200], [30, 300], [40, 400]])
    before = source.copy()
    shuffled = draw(operation, {}, source=source)
    assert shuffled.shape == source.shape
    assert Counter(map(tuple, shuffled.tolist())) == Counter(map(tuple, source.tolist()))
    np.testing.assert_array_equal(source, before)


def test_source_choice_selects_original_rows_and_preserves_zero_probability():
    source = np.array([[10, 100], [20, 200], [30, 300]])
    selected = draw('choice', {'size': 9, 'p': [0, 1, 0]}, source=source)
    np.testing.assert_array_equal(selected, np.tile(source[1], (9, 1)))


def test_paired_bootstrap_uses_one_index_for_every_field_in_an_observation():
    source = np.column_stack((np.arange(11), 100 * np.arange(11)))
    indices = draw(
        'bootstrap', {'resamples': 5, 'sample_size': 11, 'mode': 'paired'}, source=source
    )
    assert indices.shape == (5, 11)
    assert_indices(indices, len(source))
    resamples = source[indices]
    np.testing.assert_array_equal(resamples[:, :, 1], 100 * resamples[:, :, 0])


@pytest.mark.parametrize(
    'operation,parameters',
    [
        ('integers', {'high': 5}),
        ('uniform', {}),
        ('normal', {}),
        ('choice', {'n': 5}),
    ],
)
@pytest.mark.parametrize('size,shape', [([], ()), ([0, 3], (0, 3)), (0, (0,))])
def test_declared_scalar_and_empty_shapes_are_preserved(operation, parameters, size, shape):
    values = draw(operation, {**parameters, 'size': size})
    assert isinstance(values, np.ndarray)
    assert values.shape == shape


def test_stratified_sample_retains_declared_counts_and_explicit_label_order():
    groups = ['beta', 'alpha', 'beta', 'gamma', 'alpha', 'beta', 'gamma', 'alpha']
    labels, counts = ['alpha', 'beta', 'gamma'], [2, 3, 1]
    selected = draw('stratified_sample', {'groups': groups, 'labels': labels, 'counts': counts})
    assert selected.shape == (sum(counts),)
    assert_indices(selected, len(groups))
    assert len(set(selected.tolist())) == len(selected)
    np.testing.assert_array_equal(np.asarray(groups)[selected], np.repeat(labels, counts))


def test_stratified_sample_zero_counts_exclude_that_group_and_returns_source_indices():
    groups = [10, 20, 10, 30, 20, 30]
    source = np.column_stack((100 + np.arange(6), 1000 + np.arange(6)))
    selected = draw('stratified_sample', {'groups': groups, 'counts': [2, 0, 1]}, source=source)
    assert selected.shape == (3,)
    assert_indices(selected, len(source))
    np.testing.assert_array_equal(np.asarray(groups)[selected], [10, 10, 30])


def test_stratified_sampling_with_replacement_permits_requested_oversampling():
    groups = ['small', 'small', 'single']
    selected = draw('stratified_sample', {'groups': groups, 'counts': [20, 30], 'replace': True})
    assert selected.shape == (50,)
    assert_indices(selected, 3)
    np.testing.assert_array_equal(
        np.asarray(groups)[selected], np.repeat(['small', 'single'], [20, 30])
    )


def test_stratified_split_covers_all_rows_once_and_retains_each_partition_group_count():
    groups = ['a', 'a', 'a', 'b', 'b', 'b', 'c', 'c']
    labels = ['c', 'a', 'b']
    counts = np.array([[1, 0, 1], [1, 1, 1], [1, 2, 0]])
    selected = draw(
        'stratified_split', {'groups': groups, 'labels': labels, 'counts': counts.tolist()}
    )
    assert selected.shape == (len(groups),)
    np.testing.assert_array_equal(np.sort(selected), np.arange(len(groups)))
    partitions = np.split(selected, np.cumsum(counts.sum(axis=0))[:-1])
    for partition, column in zip(partitions, counts.T):
        observed = Counter(np.asarray(groups)[partition].tolist())
        assert observed == {label: int(count) for label, count in zip(labels, column) if count}


def test_stratified_split_returns_indices_when_source_observations_are_supplied():
    source = np.array([[100, 101], [200, 201], [300, 301], [400, 401]])
    selected = draw(
        'stratified_split', {'groups': [0, 1, 0, 1], 'counts': [[1, 1], [1, 1]]}, source=source
    )
    assert selected.shape == (4,)
    np.testing.assert_array_equal(np.sort(selected), np.arange(4))
    for partition in np.split(selected, 2):
        assert Counter(np.array([0, 1, 0, 1])[partition].tolist()) == {0: 1, 1: 1}


@pytest.mark.parametrize(
    'operation,parameters',
    [
        ('stratified_sample', {'groups': [0, 0, 1], 'counts': [3, 1]}),
        ('stratified_sample', {'groups': [0, 0, 1], 'counts': [1]}),
        ('stratified_sample', {'groups': [0, 'one'], 'counts': [1, 1]}),
        ('stratified_sample', {'groups': [0, 0, 1], 'labels': [0, 0], 'counts': [1, 1]}),
        ('stratified_sample', {'groups': [0, 0, 1], 'labels': [0], 'counts': [1]}),
        ('stratified_sample', {'groups': [0, 0, 1], 'counts': [1, -1]}),
        ('stratified_sample', {'groups': [0, 0, 1], 'counts': [1, 1], 'n': 4}),
        ('stratified_split', {'groups': [0, 0, 1], 'counts': [[1, 0], [0, 1]]}),
        ('stratified_split', {'groups': [0, 0, 1], 'counts': [[1, 1], [1]]}),
        ('stratified_split', {'groups': [0, 0, 1], 'counts': [[1, 1], [1, -1]]}),
    ],
)
def test_invalid_stratum_definitions_and_counts_fail_during_inspection(operation, parameters):
    with pytest.raises(ChancesError):
        chances.inspect(protocol(operation, parameters))


def test_antithetic_normal_pairs_retain_reflection_symmetry():
    values = draw('antithetic', {'n': 20, 'd': 4, 'distribution': 'normal', 'loc': 3, 'scale': 2})
    assert values.shape == (20, 4)
    np.testing.assert_allclose(values[:10] + values[10:], 6, rtol=0, atol=3e-15)
    assert not np.array_equal(values[:10], values[10:])


def test_antithetic_uniform_pairs_stay_inside_bounds_and_retain_reflection_symmetry():
    values = draw('antithetic', {'n': 20, 'd': 4, 'distribution': 'uniform', 'low': -2, 'high': 5})
    assert values.shape == (20, 4)
    assert np.all((-2 < values) & (values < 5))
    np.testing.assert_allclose(values[:10] + values[10:], 3, rtol=0, atol=1e-15)


def test_zero_variance_antithetic_normal_preserves_the_declared_constant():
    values = draw('antithetic', {'n': 8, 'd': 3, 'loc': 2.5, 'scale': 0})
    np.testing.assert_array_equal(values, np.full((8, 3), 2.5))


@pytest.mark.parametrize(
    'parameters',
    [
        {'n': 9, 'd': 2},
        {'n': 0, 'd': 2},
        {'n': 8, 'd': 0},
        {'n': 8, 'd': 2, 'distribution': 'gamma'},
        {'n': 8, 'd': 2, 'scale': -1},
        {'n': 8, 'd': 2, 'distribution': 'uniform', 'low': 1, 'high': 1},
        {'n': 8, 'd': 2, 'distribution': 'uniform', 'low': 0, 'high': 1, 'scale': 2},
    ],
)
def test_invalid_antithetic_protocols_fail_during_inspection(parameters):
    with pytest.raises(ChancesError):
        chances.inspect(protocol('antithetic', parameters))


@pytest.mark.parametrize(
    'dtype,value',
    [
        ('int32', 2**31 - 1),
        ('int64', 2**63 - 1),
        ('uint32', 2**32 - 1),
        ('uint64', 2**64 - 1),
    ],
)
def test_inclusive_integer_dtype_maximum_is_preserved_exactly(dtype, value):
    values = draw(
        'integers', {'low': value, 'high': value, 'endpoint': True, 'dtype': dtype, 'size': 7}
    )
    assert values.dtype == np.dtype(dtype)
    np.testing.assert_array_equal(values, np.full(7, value, dtype=dtype))


def test_unsigned_integer_maximum_has_a_valid_exclusive_upper_bound():
    values = draw('integers', {'low': 2**64 - 2, 'high': 2**64, 'dtype': 'uint64', 'size': 40})
    assert values.dtype == np.dtype('uint64')
    assert set(values.tolist()) <= {2**64 - 2, 2**64 - 1}


def test_antithetic_zero_variance_normal_remains_finite_near_float_maximum():
    values = draw('antithetic', {'n': 8, 'd': 3, 'loc': 1e308, 'scale': 0})
    np.testing.assert_array_equal(values, np.full((8, 3), 1e308))
