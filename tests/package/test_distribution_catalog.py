"""Exercise every advertised distribution and independently check scientific support."""

import json
from copy import deepcopy

import numpy as np
import pytest

import chances

CATALOG = chances.catalog()
DISTRIBUTIONS = CATALOG['distributions']


def protocol(name, parameters, *, size=64):
    return {
        'version': 1,
        'operation': 'distribution',
        'parameters': {'distribution': name, **parameters, 'size': size},
        'randomness': {'seed': 2026, 'stream': f'distribution/{name}'},
    }


def test_catalog_is_finite_json_with_operation_and_distribution_contracts():
    encoded = json.dumps(CATALOG, allow_nan=False)
    assert json.loads(encoded) == CATALOG
    assert CATALOG['schema_version'] == 'chances.operations.v1'
    assert {
        'integers',
        'normal',
        'bootstrap',
        'sobol',
        'halton',
        'latin_hypercube',
        'sudoku',
    } <= set(CATALOG['operations'])
    assert {
        'norm',
        'beta',
        'gamma',
        'binom',
        'poisson',
        'dirichlet',
        'multinomial',
        'multivariate_normal',
    } <= set(DISTRIBUTIONS)


@pytest.mark.parametrize('name', sorted(DISTRIBUTIONS))
def test_every_catalog_distribution_example_is_executable_and_repeatable(name):
    description = DISTRIBUTIONS[name]
    example = deepcopy(description['example'])
    spec = protocol(name, example, size=[3, 2])
    before = deepcopy(spec)
    chances.inspect(spec)
    first = chances.generate(spec)
    second = chances.generate(spec)
    assert first.data.shape[:2] == (3, 2)
    assert np.all(np.isfinite(first.data))
    np.testing.assert_array_equal(first.data, second.data)
    assert first.receipt == second.receipt
    assert spec == before
    if description['kind'] == 'discrete':
        assert np.issubdtype(first.data.dtype, np.integer)


@pytest.mark.parametrize(
    'name,parameters,lower,upper',
    [
        ('beta', {'a': 2, 'b': 5}, 0, 1),
        ('gamma', {'a': 2}, 0, None),
        ('chi2', {'df': 3}, 0, None),
        ('expon', {}, 0, None),
        ('lognorm', {'s': 0.5}, 0, None),
        ('weibull_min', {'c': 1.5}, 0, None),
        ('binom', {'n': 7, 'p': 0.4}, 0, 7),
        ('poisson', {'mu': 4}, 0, None),
        ('geom', {'p': 0.4}, 1, None),
        ('nbinom', {'n': 5, 'p': 0.5}, 0, None),
        ('randint', {'low': 3, 'high': 8}, 3, 7),
    ],
)
def test_distribution_samples_respect_mathematical_support(name, parameters, lower, upper):
    values = chances.generate(protocol(name, parameters, size=[9, 7])).data
    assert values.shape == (9, 7)
    assert np.all(values >= lower)
    if upper is not None:
        assert np.all(values <= upper)


@pytest.mark.parametrize(
    'name,parameters,expected',
    [
        ('bernoulli', {'p': 1}, 1),
        ('binom', {'n': 7, 'p': 0}, 0),
        ('binom', {'n': 7, 'p': 1}, 7),
        ('poisson', {'mu': 0}, 0),
        ('randint', {'low': 3, 'high': 4}, 3),
        ('hypergeom', {'M': 5, 'n': 5, 'N': 3}, 3),
    ],
)
def test_degenerate_discrete_distributions_preserve_exact_outcomes(name, parameters, expected):
    values = chances.generate(protocol(name, parameters, size=32)).data
    np.testing.assert_array_equal(values, np.full(32, expected))


@pytest.mark.parametrize(
    'name,parameters',
    [
        ('beta', {'a': 0, 'b': 2}),
        ('gamma', {'a': 0}),
        ('chi2', {'df': 0}),
        ('binom', {'n': -1, 'p': 0.5}),
        ('binom', {'n': 4, 'p': 1.1}),
        ('binom', {'n': 4.5, 'p': 0.5}),
        ('poisson', {'mu': -1}),
        ('geom', {'p': 0}),
        ('randint', {'low': 4, 'high': 4}),
        ('norm', {'scale': 0}),
        ('norm', {'scale': -1}),
        ('norm', {'loc': float('nan')}),
        ('beta', {'a': 2}),
    ],
)
def test_invalid_distribution_domains_fail_during_inspection(name, parameters):
    with pytest.raises(chances.ChancesError):
        chances.inspect(protocol(name, parameters))


def test_unknown_distribution_and_parameter_fail_explicitly():
    with pytest.raises(chances.ChancesError):
        chances.inspect(protocol('invented_distribution', {}))
    with pytest.raises(chances.ChancesError):
        chances.inspect(protocol('norm', {'typo_scale': 1}))


def test_dirichlet_samples_are_probability_vectors_with_explicit_event_shape():
    values = chances.generate(protocol('dirichlet', {'alpha': [1, 2, 3, 4]}, size=[3, 5])).data
    assert values.shape == (3, 5, 4)
    assert np.all((0 <= values) & (values <= 1))
    np.testing.assert_allclose(values.sum(axis=-1), 1, rtol=0, atol=1e-14)


def test_multinomial_samples_preserve_trial_count_and_impossible_categories():
    values = chances.generate(
        protocol('multinomial', {'n': 17, 'p': [0, 0.25, 0.75]}, size=[4, 5])
    ).data
    assert values.shape == (4, 5, 3)
    assert np.issubdtype(values.dtype, np.integer)
    assert np.all(values >= 0)
    np.testing.assert_array_equal(values.sum(axis=-1), np.full((4, 5), 17))
    np.testing.assert_array_equal(values[:, :, 0], np.zeros((4, 5), dtype=int))


def test_multivariate_hypergeometric_retains_population_caps_and_sample_totals():
    values = chances.generate(
        protocol('multivariate_hypergeometric', {'m': [2, 5, 7], 'n': 6}, size=32)
    ).data
    assert values.shape == (32, 3)
    assert np.issubdtype(values.dtype, np.integer)
    assert np.all((0 <= values) & (values <= [2, 5, 7]))
    np.testing.assert_array_equal(values.sum(axis=-1), np.full(32, 6))


@pytest.mark.parametrize('name', ['wishart', 'invwishart'])
def test_wishart_matrix_events_are_symmetric_positive_definite(name):
    values = chances.generate(
        protocol(name, {'df': 5, 'scale': [[1, 0.2], [0.2, 1]]}, size=[3, 2])
    ).data
    assert values.shape == (3, 2, 2, 2)
    np.testing.assert_allclose(values, values.swapaxes(-1, -2), rtol=0, atol=1e-14)
    assert np.all(np.linalg.eigvalsh(values) > 0)


def test_explicit_singular_covariance_preserves_the_declared_linear_constraint():
    values = chances.generate(
        protocol(
            'multivariate_normal',
            {
                'mean': [1, -1],
                'cov': [[1, 1], [1, 1]],
                'allow_singular': True,
            },
            size=32,
        )
    ).data
    assert values.shape == (32, 2)
    np.testing.assert_allclose(values[:, 0] - values[:, 1], 2, rtol=0, atol=1e-7)


def test_empirical_sampling_preserves_the_declared_support_and_zero_weights():
    values = chances.generate(
        protocol('empirical', {'values': [2.5, -1, 8], 'p': [0, 1, 0]}, size=32)
    ).data
    np.testing.assert_array_equal(values, np.full(32, -1))


@pytest.mark.parametrize(
    'name,parameters',
    [
        ('dirichlet', {'alpha': [1, 0, 2]}),
        ('multinomial', {'n': 5, 'p': [0.3, 0.3]}),
        ('multivariate_hypergeometric', {'m': [2, 3], 'n': 6}),
        ('multivariate_normal', {'mean': [0, 0], 'cov': [[1, 2], [2, 1]]}),
        ('multivariate_normal', {'mean': [0, 0], 'cov': [[1, 1], [1, 1]]}),
        ('multivariate_normal', {'mean': [0, 0], 'cov': [[1, 0.2], [0.1, 1]]}),
        ('multivariate_normal', {'mean': [0, 0], 'cov': [[1]]}),
        ('wishart', {'df': 1, 'scale': [[1, 0], [0, 1]]}),
        ('empirical', {'values': []}),
    ],
)
def test_invalid_vector_and_matrix_distribution_domains_fail_during_inspection(name, parameters):
    with pytest.raises(chances.ChancesError):
        chances.inspect(protocol(name, parameters))


@pytest.mark.parametrize('size,shape', [([], ()), ([0, 3], (0, 3)), (0, (0,))])
def test_scalar_and_empty_distribution_shapes_are_preserved(size, shape):
    values = chances.generate(protocol('norm', {}, size=size)).data
    assert isinstance(values, np.ndarray)
    assert values.shape == shape


@pytest.mark.parametrize(
    'name',
    sorted(
        name for name, entry in DISTRIBUTIONS.items() if entry['kind'] in {'continuous', 'discrete'}
    ),
)
def test_each_scalar_distribution_can_be_the_sole_active_mixture_component(name):
    from scipy import stats

    example = deepcopy(DISTRIBUTIONS[name]['example'])
    component = {'distribution': name, **example}
    spec = protocol(
        'mixture',
        {
            'components': [component, {'distribution': 'uniform', 'loc': 10_000, 'scale': 1}],
            'weights': [1, 0],
        },
        size=[3, 2],
    )
    values = chances.generate(spec).data
    assert values.shape == (3, 2)
    assert values.dtype == np.dtype('float64')
    lower, upper = getattr(stats, name).support(**example)
    assert np.all(values >= lower)
    assert np.all(values <= upper)
    if DISTRIBUTIONS[name]['kind'] == 'discrete':
        np.testing.assert_array_equal(values, np.floor(values))


@pytest.mark.parametrize('active', [0, 1, 2])
def test_zero_probability_mixture_components_cannot_contribute_support(active):
    weights = [0, 0, 0]
    weights[active] = 1
    values = chances.generate(
        protocol(
            'mixture',
            {
                'components': [
                    {'distribution': 'uniform', 'loc': -100, 'scale': 1},
                    {'distribution': 'uniform', 'loc': 10, 'scale': 2},
                    {'distribution': 'uniform', 'loc': 1000, 'scale': 3},
                ],
                'weights': weights,
            },
            size=100,
        )
    ).data
    low, high = [(-100, -99), (10, 12), (1000, 1003)][active]
    assert np.all((low <= values) & (values <= high))


def test_mixture_samples_belong_to_the_union_of_active_disjoint_supports():
    values = chances.generate(
        protocol(
            'mixture',
            {
                'components': [
                    {'distribution': 'uniform', 'loc': 0, 'scale': 1},
                    {'distribution': 'uniform', 'loc': 10, 'scale': 1},
                    {'distribution': 'uniform', 'loc': 20, 'scale': 1},
                ],
                'weights': [0.5, 0, 0.5],
            },
            size=[12, 9],
        )
    ).data
    assert np.all(((0 <= values) & (values <= 1)) | ((20 <= values) & (values <= 21)))


def test_discrete_mixture_retains_exact_degenerate_component_outcomes():
    values = chances.generate(
        protocol(
            'mixture',
            {
                'components': [
                    {'distribution': 'binom', 'n': 0, 'p': 0.5, 'loc': -3},
                    {'distribution': 'poisson', 'mu': 0, 'loc': 5},
                ],
                'weights': [0.4, 0.6],
            },
            size=[12, 9],
        )
    ).data
    assert set(values.ravel().tolist()) <= {-3.0, 5.0}


@pytest.mark.parametrize(
    'parameters',
    [
        {'components': [], 'weights': []},
        {'components': [{'distribution': 'norm'}], 'weights': [0.5, 0.5]},
        {'components': [{'distribution': 'norm'}], 'weights': [-1]},
        {'components': [{'distribution': 'norm'}], 'weights': [0.8]},
        {'components': [{'distribution': 'norm', 'size': 3}], 'weights': [1]},
        {'components': [{'distribution': 'norm', 'scale': 0}], 'weights': [1]},
        {'components': [{'distribution': 'dirichlet', 'alpha': [1, 2]}], 'weights': [1]},
        {
            'components': [{'distribution': 'mixture', 'components': [], 'weights': []}],
            'weights': [1],
        },
        {'components': [{'distribution': 'not_registered'}], 'weights': [1]},
    ],
)
def test_invalid_mixture_protocols_fail_during_inspection(parameters):
    with pytest.raises(chances.ChancesError):
        chances.inspect(protocol('mixture', parameters))


def test_empirical_integer_support_cannot_silently_round_in_float64():
    with pytest.raises(chances.ChancesError):
        chances.inspect(protocol('empirical', {'values': [2**53 + 1]}))


def test_nonrepresentable_discrete_mixture_outcome_cannot_silently_round():
    with pytest.raises(chances.ChancesError):
        chances.generate(
            protocol(
                'mixture',
                {
                    'components': [{'distribution': 'binom', 'n': 0, 'p': 0.5, 'loc': 2**53 + 1}],
                    'weights': [1],
                },
            )
        )


@pytest.mark.parametrize(
    'parameters',
    [
        {'n': 4, 'p': [0.5, 0.5000000000001]},
        {'n': 4, 'p': [0.5, 0.4999999999999]},
    ],
)
def test_multinomial_probabilities_must_pass_the_executor_domain_at_inspection(parameters):
    with pytest.raises(chances.ChancesError):
        chances.inspect(protocol('multinomial', parameters))


@pytest.mark.parametrize('location', [-(2**63), 2**53 + 1, 2**63 - 1])
def test_discrete_location_preserves_integer_precision_and_int64_endpoints(location):
    values = chances.generate(protocol('binom', {'n': 0, 'p': 0.5, 'loc': location}, size=7)).data
    assert values.dtype == np.dtype('int64')
    np.testing.assert_array_equal(values, np.full(7, location, dtype='int64'))


def test_exactly_representable_empirical_integer_above_consecutive_float_precision_is_preserved():
    expected = 2**53 + 2
    values = chances.generate(protocol('empirical', {'values': [expected]}, size=7)).data
    np.testing.assert_array_equal(values, np.full(7, float(expected)))
