"""Explicit SciPy distribution adapters; names never select arbitrary objects."""

from __future__ import annotations

import math
import warnings
from copy import deepcopy
from typing import NoReturn

import numpy as np
from scipy import stats

from ._errors import ChancesError

# Each registered name and each public parameter are deliberately enumerated.
# Example shape arguments are executable, valid specifications, not defaults.
_CONTINUOUS = {
    'alpha': {'a': 2.0},
    'anglit': {},
    'arcsine': {},
    'argus': {'chi': 1.0},
    'beta': {'a': 2.0, 'b': 3.0},
    'betaprime': {'a': 2.0, 'b': 3.0},
    'bradford': {'c': 1.0},
    'burr': {'c': 2.0, 'd': 3.0},
    'burr12': {'c': 2.0, 'd': 3.0},
    'cauchy': {},
    'chi': {'df': 3.0},
    'chi2': {'df': 3.0},
    'cosine': {},
    'crystalball': {'beta': 2.0, 'm': 3.0},
    'dgamma': {'a': 2.0},
    'dweibull': {'c': 2.0},
    'erlang': {'a': 2},
    'expon': {},
    'exponnorm': {'K': 1.0},
    'exponpow': {'b': 2.0},
    'exponweib': {'a': 2.0, 'c': 2.0},
    'f': {'dfn': 5.0, 'dfd': 10.0},
    'fatiguelife': {'c': 1.0},
    'fisk': {'c': 3.0},
    'foldcauchy': {'c': 1.0},
    'foldnorm': {'c': 1.0},
    'gamma': {'a': 2.0},
    'gausshyper': {'a': 2.0, 'b': 3.0, 'c': 1.0, 'z': 0.5},
    'genexpon': {'a': 1.0, 'b': 1.0, 'c': 1.0},
    'genextreme': {'c': 0.1},
    'gengamma': {'a': 2.0, 'c': 1.0},
    'genhalflogistic': {'c': 1.0},
    'genhyperbolic': {'p': 1.0, 'a': 2.0, 'b': 0.5},
    'geninvgauss': {'p': 1.0, 'b': 2.0},
    'genlogistic': {'c': 2.0},
    'gennorm': {'beta': 2.0},
    'genpareto': {'c': 0.1},
    'gibrat': {},
    'gompertz': {'c': 1.0},
    'gumbel_l': {},
    'gumbel_r': {},
    'halfcauchy': {},
    'halfgennorm': {'beta': 2.0},
    'halflogistic': {},
    'halfnorm': {},
    'hypsecant': {},
    'invgamma': {'a': 3.0},
    'invgauss': {'mu': 1.0},
    'invweibull': {'c': 3.0},
    'johnsonsb': {'a': 1.0, 'b': 2.0},
    'johnsonsu': {'a': 1.0, 'b': 2.0},
    'kappa3': {'a': 2.0},
    'kappa4': {'h': 1.0, 'k': 1.0},
    'ksone': {'n': 10},
    'kstwo': {'n': 10},
    'kstwobign': {},
    'laplace': {},
    'laplace_asymmetric': {'kappa': 1.0},
    'levy': {},
    'levy_l': {},
    'loggamma': {'c': 2.0},
    'logistic': {},
    'loglaplace': {'c': 2.0},
    'lognorm': {'s': 1.0},
    'loguniform': {'a': 1.0, 'b': 10.0},
    'lomax': {'c': 3.0},
    'maxwell': {},
    'mielke': {'k': 2.0, 's': 3.0},
    'moyal': {},
    'nakagami': {'nu': 1.0},
    'ncf': {'dfn': 5.0, 'dfd': 10.0, 'nc': 1.0},
    'nct': {'df': 5.0, 'nc': 1.0},
    'ncx2': {'df': 5.0, 'nc': 1.0},
    'norm': {},
    'norminvgauss': {'a': 2.0, 'b': 0.5},
    'pareto': {'b': 3.0},
    'pearson3': {'skew': 1.0},
    'powerlaw': {'a': 2.0},
    'powerlognorm': {'c': 2.0, 's': 1.0},
    'powernorm': {'c': 2.0},
    'rayleigh': {},
    'rdist': {'c': 3.0},
    'recipinvgauss': {'mu': 1.0},
    'reciprocal': {'a': 1.0, 'b': 10.0},
    'rice': {'b': 1.0},
    'semicircular': {},
    'skewcauchy': {'a': 0.5},
    'skewnorm': {'a': 1.0},
    'studentized_range': {'k': 3.0, 'df': 10.0},
    't': {'df': 5.0},
    'trapezoid': {'c': 0.25, 'd': 0.75},
    'triang': {'c': 0.5},
    'truncexpon': {'b': 2.0},
    'truncnorm': {'a': -1.0, 'b': 1.0},
    'truncpareto': {'b': 3.0, 'c': 10.0},
    'truncweibull_min': {'c': 2.0, 'a': 0.1, 'b': 2.0},
    'tukeylambda': {'lam': 0.5},
    'uniform': {},
    'vonmises': {'kappa': 1.0},
    'vonmises_line': {'kappa': 1.0},
    'wald': {},
    'weibull_max': {'c': 2.0},
    'weibull_min': {'c': 2.0},
    'wrapcauchy': {'c': 0.5},
}
_DISCRETE = {
    'bernoulli': {'p': 0.5},
    'betabinom': {'n': 10, 'a': 2.0, 'b': 3.0},
    'binom': {'n': 10, 'p': 0.5},
    'boltzmann': {'lambda_': 1.0, 'N': 10},
    'dlaplace': {'a': 1.0},
    'geom': {'p': 0.5},
    'hypergeom': {'M': 30, 'n': 10, 'N': 5},
    'logser': {'p': 0.5},
    'nbinom': {'n': 3.0, 'p': 0.5},
    'nchypergeom_fisher': {'M': 30, 'n': 10, 'N': 5, 'odds': 1.0},
    'nchypergeom_wallenius': {'M': 30, 'n': 10, 'N': 5, 'odds': 1.0},
    'nhypergeom': {'M': 30, 'n': 10, 'r': 5},
    'planck': {'lambda_': 1.0},
    'poisson': {'mu': 3.0},
    'randint': {'low': 0, 'high': 10},
    'skellam': {'mu1': 3.0, 'mu2': 2.0},
    'yulesimon': {'alpha': 3.0},
    'zipf': {'a': 3.0},
    'zipfian': {'a': 2.0, 'n': 10},
}
_INTEGER_SHAPES = {
    'erlang': {'a'},
    'ksone': {'n'},
    'kstwo': {'n'},
    'betabinom': {'n'},
    'binom': {'n'},
    'boltzmann': {'N'},
    'hypergeom': {'M', 'n', 'N'},
    'nchypergeom_fisher': {'M', 'n', 'N'},
    'nchypergeom_wallenius': {'M', 'n', 'N'},
    'nhypergeom': {'M', 'n', 'r'},
    'randint': {'low', 'high'},
    'zipfian': {'n'},
}
# getattr here only sees literal registered names; user inputs index this map.
_UNIVARIATE = {name: getattr(stats, name) for name in (*_CONTINUOUS, *_DISCRETE)}
_MULTIVARIATE = {
    'dirichlet': {'alpha': [1.0, 2.0, 3.0]},
    'multinomial': {'n': 10, 'p': [0.2, 0.3, 0.5]},
    'multivariate_normal': {'mean': [0.0, 0.0], 'cov': [[1.0, 0.0], [0.0, 1.0]]},
    'multivariate_t': {'loc': [0.0, 0.0], 'shape': [[1.0, 0.0], [0.0, 1.0]], 'df': 5.0},
    'wishart': {'df': 5.0, 'scale': [[1.0, 0.0], [0.0, 1.0]]},
    'invwishart': {'df': 5.0, 'scale': [[1.0, 0.0], [0.0, 1.0]]},
    'multivariate_hypergeometric': {'m': [10, 10, 10], 'n': 5},
    'empirical': {'values': [1.0, 2.0, 3.0]},
}
_MULTIVARIATE_OBJECTS = {
    'dirichlet': stats.dirichlet,
    'multinomial': stats.multinomial,
    'multivariate_normal': stats.multivariate_normal,
    'multivariate_t': stats.multivariate_t,
    'wishart': stats.wishart,
    'invwishart': stats.invwishart,
    'multivariate_hypergeometric': stats.multivariate_hypergeom,
}


def fail(message: str, **details: object) -> NoReturn:
    raise ChancesError('INVALID_PARAMETERS', message, details)


def integer(value: object, key: str, minimum: int | None = None) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        fail(f'{key} must be an integer', parameter=key)
    value = int(value)
    if minimum is not None and value < minimum:
        fail(f'{key} must be at least {minimum}', parameter=key)
    if not -(2**63) <= value < 2**63:
        fail(f'{key} must fit a signed 64-bit integer', parameter=key)
    return value


def number(value: object, key: str, minimum: float | None = None, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        fail(f'{key} must be a finite number', parameter=key)
    try:
        value = float(value)
    except (OverflowError, ValueError):
        fail(f'{key} must be a finite number', parameter=key)
    if not math.isfinite(value):
        fail(f'{key} must be finite', parameter=key)
    if (minimum is not None and value < minimum) or (positive and value <= 0):
        fail(f'{key} is outside its supported domain', parameter=key)
    return value


def boolean(value: object, key: str) -> bool:
    if type(value) is not bool:
        fail(f'{key} must be a boolean', parameter=key)
    return value


def size_shape(value: object) -> tuple[int, ...]:
    if isinstance(value, list):
        if len(value) > 16:
            fail('size supports at most 16 dimensions', parameter='size')
        return tuple(integer(v, 'size', 0) for v in value)
    return (integer(value, 'size', 0),)


def vector(value: object, key: str, positive: bool = False, integral: bool = False) -> list:
    if not isinstance(value, list) or not value:
        fail(f'{key} must be a nonempty list', parameter=key)
    return [integer(v, key, 0) if integral else number(v, key, positive=positive) for v in value]


def probabilities(value: object, n: int, key: str = 'p') -> list[float]:
    out = vector(value, key)
    if len(out) != n or any(v < 0 or v > 1 for v in out):
        fail(f'{key} must contain {n} nonnegative probabilities', parameter=key)
    if (
        not math.isclose(math.fsum(out), 1.0, rel_tol=0.0, abs_tol=1e-15)
        or abs(float(np.sum(out)) - 1.0) > 1e-15
    ):
        fail(f'{key} must sum to one', parameter=key)
    return out


def _matrix(value: object, key: str, d: int | None, limits: dict, singular: bool = False) -> list:
    if not isinstance(value, list) or not value or any(not isinstance(row, list) for row in value):
        fail(f'{key} must be a square matrix', parameter=key)
    dim = len(value)
    if (d is not None and dim != d) or any(len(row) != dim for row in value):
        fail(f'{key} dimensions do not match', parameter=key)
    _resource((dim, dim), limits, work=dim**3, scratch=4)
    matrix = np.array([[number(v, key) for v in row] for row in value], dtype=np.float64)
    if not np.array_equal(matrix, matrix.T):
        fail(f'{key} must be symmetric', parameter=key)
    try:
        if singular:
            eigenvalues = np.linalg.eigvalsh(matrix)
            if np.any(eigenvalues < 0):
                fail(f'{key} must be positive semidefinite', parameter=key)
        else:
            np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError:
        fail(f'{key} must be positive definite', parameter=key)
    return matrix.tolist()


def _resource(
    shape: tuple[int, ...],
    limits: dict,
    *,
    work: int | None = None,
    scratch: int = 3,
    itemsize: int = 8,
) -> None:
    if len(shape) > 16:
        fail('Output supports at most 16 dimensions', parameter='size')
    values = math.prod(shape)
    estimates = {
        'max_values': values,
        'max_bytes': values * itemsize * scratch,
        'max_work': values if work is None else work,
    }
    for key, required in estimates.items():
        if required > limits[key]:
            raise ChancesError(
                'RESOURCE_LIMIT',
                f'{key} would be exceeded',
                {'limit': key, 'required': required, 'allowed': limits[key]},
            )


def distribution_catalog() -> dict:
    out = {}
    for kind, registry in [('continuous', _CONTINUOUS), ('discrete', _DISCRETE)]:
        for name, example in registry.items():
            params = {
                key: {
                    'required': True,
                    'type': 'integer'
                    if key in _INTEGER_SHAPES.get(name, set())
                    else 'finite_number',
                }
                for key in example
            }
            params.update(
                {
                    'size': {'default': 1, 'type': 'integer_or_shape'},
                    'loc': {'default': 0 if kind == 'discrete' else 0.0},
                }
            )
            if kind == 'continuous':
                params['scale'] = {'default': 1.0, 'constraint': 'strictly positive'}
            out[name] = {
                'kind': kind,
                'shape_parameters': list(example),
                'parameters': params,
                'example': deepcopy(example),
                'output': 'size shape; float64 continuous or int64 discrete',
                'constraints': 'Finite scalar parameters; SciPy public support validates the distribution domain. loc is an integer for discrete distributions.',
            }
    for name, example in _MULTIVARIATE.items():
        optional = (
            {'allow_singular': {'default': False}}
            if name in ('multivariate_normal', 'multivariate_t')
            else {}
        )
        if name == 'empirical':
            optional['p'] = {'default': None}
        out[name] = {
            'kind': 'empirical' if name == 'empirical' else 'multivariate',
            'shape_parameters': list(example),
            'parameters': {
                **{key: {'required': True} for key in example},
                'size': {'default': 1, 'type': 'integer_or_shape'},
                **optional,
            },
            'example': deepcopy(example),
            'output': 'size shape'
            if name == 'empirical'
            else 'size shape followed by vector dimension or matrix dimensions (Wishart)',
            'constraints': 'Finite arrays; probability vectors sum to one within 1e-15; covariance/scale matrices symmetric positive definite unless allow_singular explicitly permits semidefinite covariance.',
        }
    out['mixture'] = {
        'kind': 'mixture',
        'shape_parameters': ['components', 'weights'],
        'parameters': {
            'components': {'required': True, 'maximum_length': 256},
            'weights': {'required': True},
            'size': {'default': 1},
        },
        'example': {
            'components': [
                {'distribution': 'norm', 'loc': -2.0},
                {'distribution': 'norm', 'loc': 2.0},
            ],
            'weights': [0.4, 0.6],
        },
        'output': 'size shape; float64; component assignment order preserved',
        'constraints': '1..256 explicit registered univariate SciPy components; no component size, mixture recursion, vectors or callbacks. All components validate even when weight is zero. Weights sum to one within 1e-15. Discrete component draws must lie within [-2**53,2**53] for exact float64 conversion. Mixed observations are IID under the declared mixture law; the implementation draws assignments then batches component draws.',
    }
    out['truncnorm']['constraints'] += (
        ' a and b are standardized bounds relative to loc and scale, not absolute endpoints.'
    )
    out['vonmises']['constraints'] += (
        ' Circular variates; this is not the bounded vonmises_line distribution.'
    )
    out['multivariate_t']['parameters']['df']['constraint'] = 'finite and strictly positive'
    return out


def resolve_distribution(parameters: dict, limits: dict) -> dict:
    name = parameters.get('distribution')
    if not isinstance(name, str) or name not in (*_UNIVARIATE, *_MULTIVARIATE, 'mixture'):
        raise ChancesError(
            'UNKNOWN_DISTRIBUTION', 'Distribution is not registered', {'distribution': name}
        )
    shape = size_shape(parameters.get('size', 1))
    if name == 'mixture':
        return _resolve_mixture(parameters, limits, shape)
    if name in _UNIVARIATE:
        return _resolve_univariate(name, parameters, limits, shape)
    return _resolve_multivariate(name, parameters, limits, shape)


def _resolve_univariate(name: str, parameters: dict, limits: dict, shape: tuple[int, ...]) -> dict:
    registry = _CONTINUOUS if name in _CONTINUOUS else _DISCRETE
    shape_names = registry[name]
    allowed = {'distribution', 'size', 'loc', *shape_names}
    if name in _CONTINUOUS:
        allowed.add('scale')
    _unknown(parameters, allowed)
    for key in shape_names:
        if key not in parameters:
            fail(f'{key} is required for {name}', parameter=key)
    out = {'distribution': name, 'size': parameters.get('size', 1)}
    for key in shape_names:
        out[key] = (
            integer(parameters[key], key)
            if key in _INTEGER_SHAPES.get(name, set())
            else number(parameters[key], key)
        )
    out['loc'] = (
        number(parameters.get('loc', 0.0), 'loc')
        if name in _CONTINUOUS
        else integer(parameters.get('loc', 0), 'loc')
    )
    if name in _CONTINUOUS:
        out['scale'] = number(parameters.get('scale', 1.0), 'scale', positive=True)
    _resource(shape, limits, work=math.prod(shape) * 16)
    arguments = {key: out[key] for key in shape_names}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        support = _UNIVARIATE[name].support(**arguments)
    if any(np.isnan(bound) for bound in support):
        fail(f'{name} shape parameters are outside the supported domain', distribution=name)
    if name in _DISCRETE:
        # A location shift must preserve bounded support representability.
        lo, hi = support
        for bound in (lo, hi):
            if math.isfinite(bound) and not -(2**63) <= int(bound) + out['loc'] < 2**63:
                fail('Discrete support exceeds int64', distribution=name)
    return out


def _resolve_multivariate(
    name: str, parameters: dict, limits: dict, shape: tuple[int, ...]
) -> dict:
    example = _MULTIVARIATE[name]
    allowed = {'distribution', 'size', *example}
    if name in ('multivariate_normal', 'multivariate_t'):
        allowed.add('allow_singular')
    if name == 'empirical':
        allowed.add('p')
    _unknown(parameters, allowed)
    for key in example:
        if key not in parameters:
            fail(f'{key} is required for {name}', parameter=key)
    out = {'distribution': name, 'size': parameters.get('size', 1)}
    if name in ('dirichlet', 'multinomial', 'multivariate_hypergeometric'):
        event = _resolve_count_vector(name, parameters, out)
    elif name in ('multivariate_normal', 'multivariate_t'):
        event = _resolve_covariance(name, parameters, out, limits)
    elif name in ('wishart', 'invwishart'):
        event = _resolve_wishart(parameters, out, limits)
    else:
        event = _resolve_empirical(parameters, out, limits)
    # Covariance factorization and output scratch are additional to the output.
    d = math.prod(event) if event else 1
    _resource(shape + event, limits, work=math.prod(shape) * max(16, d * d), scratch=4)
    return out


def _unknown(parameters: dict, allowed: set) -> None:
    extras = set(parameters) - allowed
    if extras:
        raise ChancesError(
            'UNKNOWN_PARAMETERS', 'Unknown operation parameter', {'parameters': sorted(extras)}
        )


def distribution_output(parameters: dict) -> tuple[tuple[int, ...], np.dtype]:
    name = parameters['distribution']
    event = ()
    if name in ('dirichlet', 'multinomial', 'multivariate_hypergeometric'):
        key = {'dirichlet': 'alpha', 'multinomial': 'p', 'multivariate_hypergeometric': 'm'}[name]
        event = (len(parameters[key]),)
    elif name in ('multivariate_normal', 'multivariate_t'):
        event = (len(parameters['mean' if name == 'multivariate_normal' else 'loc']),)
    elif name in ('wishart', 'invwishart'):
        d = len(parameters['scale'])
        event = (d, d)
    integral = name in _DISCRETE or name in ('multinomial', 'multivariate_hypergeometric')
    return size_shape(parameters['size']) + event, np.dtype('int64' if integral else 'float64')


def execute_distribution(parameters: dict, rng: np.random.Generator) -> np.ndarray:
    name = parameters['distribution']
    shape, dtype = distribution_output(parameters)
    size = size_shape(parameters['size'])
    if math.prod(size) == 0:
        return np.empty(shape, dtype=dtype)
    arguments = {
        key: value for key, value in parameters.items() if key not in ('distribution', 'size')
    }
    discrete_loc = arguments.pop('loc') if name in _DISCRETE else 0
    if name == 'mixture':
        return _execute_mixture(parameters, rng)
    if name == 'empirical':
        result = rng.choice(
            np.asarray(arguments['values'], dtype=np.float64), size=size, p=arguments['p']
        )
    elif name in _UNIVARIATE:
        with warnings.catch_warnings():
            # Numerical warnings must become failures through finite-output
            # checks, rather than contaminate the CLI's JSON output.
            warnings.simplefilter('ignore', RuntimeWarning)
            result = _UNIVARIATE[name].rvs(size=size, random_state=rng, **arguments)
    elif name in ('multivariate_normal', 'multivariate_t'):
        # rvs has no allow_singular argument; the constructor validates it.
        allow_singular = arguments.pop('allow_singular')
        frozen = _MULTIVARIATE_OBJECTS[name](**arguments, allow_singular=allow_singular)
        result = frozen.rvs(size=size, random_state=rng)
    else:
        result = _MULTIVARIATE_OBJECTS[name].rvs(size=size, random_state=rng, **arguments)
    result = np.asarray(result)
    if dtype.kind == 'i':
        result = _checked_discrete(name, parameters, result, discrete_loc)
    return np.asarray(result, dtype=dtype).reshape(shape)


def _resolve_mixture(parameters: dict, limits: dict, shape: tuple[int, ...]) -> dict:
    _unknown(parameters, {'distribution', 'size', 'components', 'weights'})
    components = parameters.get('components')
    if not isinstance(components, list) or not components:
        fail(
            'components must be a nonempty list of scalar distribution objects',
            parameter='components',
        )
    count = len(components)
    if count > 256:
        raise ChancesError(
            'RESOURCE_LIMIT',
            'Mixtures permit at most 256 components',
            {'required': count, 'allowed': 256},
        )
    draws = math.prod(shape)
    _resource((count,), limits, work=count * 64, scratch=64)
    _resource(shape, limits, work=draws * (32 + 2 * count) + count * 64, scratch=8)
    if draws * 64 + count * 512 > limits['max_bytes']:
        raise ChancesError(
            'RESOURCE_LIMIT',
            'Mixture output, assignments and scratch exceed max_bytes',
            {
                'limit': 'max_bytes',
                'required': draws * 64 + count * 512,
                'allowed': limits['max_bytes'],
            },
        )
    weights = probabilities(parameters.get('weights'), count, 'weights')
    resolved = []
    for index, component in enumerate(components):
        if (
            not isinstance(component, dict)
            or not isinstance(component.get('distribution'), str)
            or component['distribution'] not in _UNIVARIATE
        ):
            fail(
                'Every mixture component must be a registered scalar SciPy distribution',
                parameter='components',
                component=index,
            )
        if 'size' in component:
            fail(
                'Mixture components must not declare size', parameter='components', component=index
            )
        item = resolve_distribution({**component, 'size': 1}, limits)
        item.pop('size')
        if item['distribution'] in _DISCRETE:
            shape_arguments = {key: item[key] for key in _DISCRETE[item['distribution']]}
            lo, hi = _UNIVARIATE[item['distribution']].support(**shape_arguments)
            if (math.isfinite(lo) and int(lo) + item['loc'] < -(2**53)) or (
                math.isfinite(hi) and int(hi) + item['loc'] > 2**53
            ):
                fail(
                    'Discrete mixture support must permit exact float64 conversion',
                    parameter='components',
                    component=index,
                )
        resolved.append(item)
    return {
        'distribution': 'mixture',
        'size': deepcopy(parameters.get('size', 1)),
        'components': resolved,
        'weights': weights,
    }


def _execute_mixture(parameters: dict, rng: np.random.Generator) -> np.ndarray:
    shape = size_shape(parameters['size'])
    draws = math.prod(shape)
    if draws == 0:
        return np.empty(shape, dtype=np.float64)
    assignments = rng.choice(len(parameters['components']), size=draws, p=parameters['weights'])
    out = np.empty(draws, dtype=np.float64)
    for index, component in enumerate(parameters['components']):
        rows = np.flatnonzero(assignments == index)
        if not rows.size:
            continue
        values = execute_distribution({**component, 'size': int(rows.size)}, rng)
        if values.dtype.kind in 'iu' and (np.any(values < -(2**53)) or np.any(values > 2**53)):
            raise ChancesError(
                'NONFINITE_RESULT',
                'Discrete mixture draw exceeds exact float64 integer range',
                {'component': index},
            )
        out[rows] = values
    return out.reshape(shape)


def distribution_support(parameters: dict) -> dict:
    """JSON-compatible mathematical support metadata for resolved parameters."""
    name = parameters['distribution']
    if name in _UNIVARIATE:
        return _univariate_support(name, parameters)
    if name == 'mixture':
        components = [
            distribution_support(component)
            for component, weight in zip(parameters['components'], parameters['weights'])
            if weight > 0
        ]
        return {'kind': 'union', 'components': components}
    if name == 'empirical':
        return {
            'kind': 'finite_values',
            'values': [
                value
                for index, value in enumerate(parameters['values'])
                if parameters['p'] is None or parameters['p'][index] > 0
            ],
        }
    if name == 'dirichlet':
        return {'kind': 'simplex', 'low': 0.0, 'high': 1.0, 'sum': 1.0, 'tolerance': 1e-12}
    if name in ('multinomial', 'multivariate_hypergeometric'):
        support = {'kind': 'integer_simplex', 'low': 0, 'sum': parameters['n']}
        support['high'] = (
            parameters['m'][:]
            if name == 'multivariate_hypergeometric'
            else [parameters['n'] if p > 0 else 0 for p in parameters['p']]
        )
        return support
    if name in ('wishart', 'invwishart'):
        return {'kind': 'positive_definite_matrix', 'symmetric': True}
    return {'kind': 'finite_real_vector', 'low': None, 'high': None}


def _resolve_count_vector(name: str, parameters: dict, out: dict) -> tuple[int, ...]:
    if name == 'dirichlet':
        out['alpha'] = vector(parameters['alpha'], 'alpha', positive=True)
        event = (len(out['alpha']),)
    elif name == 'multinomial':
        out['n'] = integer(parameters['n'], 'n', 0)
        out['p'] = probabilities(
            parameters['p'], len(parameters['p']) if isinstance(parameters['p'], list) else 0
        )
        event = (len(out['p']),)
    elif name == 'multivariate_hypergeometric':
        out['m'] = vector(parameters['m'], 'm', integral=True)
        out['n'] = integer(parameters['n'], 'n', 0)
        if sum(out['m']) < out['n'] or sum(out['m']) >= 2**63:
            fail('n must not exceed the total population, which must fit int64')
        event = (len(out['m']),)
    return event


def _resolve_covariance(name: str, parameters: dict, out: dict, limits: dict) -> tuple[int, ...]:
    location_key, covariance_key = (
        ('mean', 'cov') if name == 'multivariate_normal' else ('loc', 'shape')
    )
    out[location_key] = vector(parameters[location_key], location_key)
    d = len(out[location_key])
    out['allow_singular'] = boolean(parameters.get('allow_singular', False), 'allow_singular')
    out[covariance_key] = _matrix(
        parameters[covariance_key], covariance_key, d, limits, out['allow_singular']
    )
    if name == 'multivariate_t':
        out['df'] = number(parameters['df'], 'df', positive=True)
    event = (d,)
    return event


def _resolve_wishart(parameters: dict, out: dict, limits: dict) -> tuple[int, ...]:
    out['scale'] = _matrix(parameters['scale'], 'scale', None, limits)
    d = len(out['scale'])
    out['df'] = number(parameters['df'], 'df', positive=True)
    if out['df'] <= d - 1:
        fail('df must be greater than matrix dimension minus one', parameter='df')
    event = (d, d)
    return event


def _resolve_empirical(parameters: dict, out: dict, limits: dict) -> tuple[int, ...]:
    values = parameters['values']
    if isinstance(values, list):
        for value in values:
            if type(value) is int and int(number(value, 'values')) != value:
                fail('Integer empirical values must convert to float64 exactly', parameter='values')
    out['values'] = vector(values, 'values')
    out['p'] = (
        None if parameters.get('p') is None else probabilities(parameters['p'], len(out['values']))
    )
    _resource((len(out['values']),), limits)
    event = ()
    return event


def _checked_discrete(
    name: str, parameters: dict, result: np.ndarray, discrete_loc: int
) -> np.ndarray:
    if result.dtype.kind == 'f' and (
        not np.isfinite(result).all() or np.any(result >= 2**63) or np.any(result < -(2**63))
    ):
        raise ChancesError(
            'NONFINITE_RESULT',
            'Discrete draw cannot be represented as int64',
            {'distribution': name},
        )
    if result.dtype.kind == 'u' and np.any(result > np.iinfo(np.int64).max):
        raise ChancesError(
            'NONFINITE_RESULT', 'Discrete draw exceeds int64', {'distribution': name}
        )
    if name in _DISCRETE:
        shape_arguments = {key: parameters[key] for key in _DISCRETE[name]}
        lo, hi = _UNIVARIATE[name].support(**shape_arguments)
        if np.any(result < lo) or np.any(result > hi):
            raise ChancesError(
                'SAMPLING_FAILED',
                'Discrete draw is outside its mathematical support',
                {'distribution': name},
            )
        minimum, maximum = int(np.min(result)), int(np.max(result))
        if minimum + discrete_loc < -(2**63) or maximum + discrete_loc >= 2**63:
            raise ChancesError(
                'NONFINITE_RESULT', 'Shifted discrete draw exceeds int64', {'distribution': name}
            )
        # Check before integer addition; SciPy loc addition can wrap.
        result = np.asarray(result, dtype=np.int64) + np.int64(discrete_loc)
    return result


def _univariate_support(name: str, parameters: dict) -> dict:
    registry = _CONTINUOUS if name in _CONTINUOUS else _DISCRETE
    args = {key: parameters[key] for key in registry[name]}
    lo, hi = _UNIVARIATE[name].support(**args)
    loc, scale = parameters.get('loc', 0), parameters.get('scale', 1)
    if name in ('bernoulli', 'binom') and parameters['p'] in (0.0, 1.0):
        lo = hi = (1 if name == 'bernoulli' else parameters['n']) * int(parameters['p'])
    elif (name == 'poisson' and parameters['mu'] == 0) or (
        name == 'nbinom' and parameters['p'] == 1
    ):
        lo = hi = 0
    elif name == 'geom' and parameters['p'] == 1:
        lo = hi = 1
    if name in _DISCRETE:
        low = int(lo) + loc if math.isfinite(lo) else None
        high = int(hi) + loc if math.isfinite(hi) else None
    else:
        with np.errstate(over='ignore', invalid='ignore'):
            lower, upper = float(lo) * scale + loc, float(hi) * scale + loc
        low = lower if math.isfinite(lower) else None
        high = upper if math.isfinite(upper) else None
    return {
        'kind': 'interval',
        'low': low,
        'high': high,
        'lower_inclusive': True,
        'upper_inclusive': True,
        'integral': name in _DISCRETE,
    }
