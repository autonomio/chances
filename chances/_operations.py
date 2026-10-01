"""Validated scientific operations with local RNGs and declared output shapes."""

from __future__ import annotations

import math
from copy import deepcopy

import numpy as np
from scipy.stats import qmc

from ._distributions import (
    boolean,
    distribution_catalog,
    distribution_output,
    distribution_support,
    execute_distribution,
    fail,
    integer,
    number,
    probabilities,
    resolve_distribution,
    size_shape,
)
from ._errors import ChancesError

_DEFAULT_LIMITS = {'max_values': 10_000_000, 'max_bytes': 268_435_456, 'max_work': 100_000_000}
_OPERATIONS = {
    'integers': {
        'parameters': {
            'low': {'default': 0},
            'high': {'required': True},
            'size': {'default': 1},
            'endpoint': {'default': False},
            'dtype': {'default': 'int64', 'choices': ['int32', 'int64', 'uint32', 'uint64']},
        },
        'source': 'forbidden',
        'output': 'size shape; declared integer dtype',
        'constraints': 'low <= value < high, or <= high with endpoint=True. Bounds must fit dtype; booleans are not integers.',
    },
    'uniform': {
        'parameters': {'low': {'default': 0.0}, 'high': {'default': 1.0}, 'size': {'default': 1}},
        'source': 'forbidden',
        'output': 'size shape; float64',
        'constraints': 'Finite low < high and finite width; output is clamped below high if floating rounding reaches the endpoint.',
    },
    'normal': {
        'parameters': {'loc': {'default': 0.0}, 'scale': {'default': 1.0}, 'size': {'default': 1}},
        'source': 'forbidden',
        'output': 'size shape; float64',
        'constraints': 'Finite location and nonnegative scale. scale=0 produces a constant array.',
    },
    'choice': {
        'parameters': {
            'n': {'required': 'when source is absent'},
            'size': {'default': 1},
            'replace': {'default': True},
            'p': {'default': None},
        },
        'source': 'optional; observations are rows along axis zero',
        'output': 'size shape of int64 indices when source absent; size shape followed by source row shape otherwise',
        'constraints': 'Nonnegative probabilities sum to one. Without replacement the full output has no repeated population indices; sufficient positive-probability outcomes are required.',
    },
    'permutation': {
        'parameters': {'n': {'required': 'when source is absent'}},
        'source': 'optional; rows along axis zero',
        'output': 'int64 permutation of range(n), or complete source rows in permuted order',
        'constraints': 'Every population index occurs exactly once. Source is never modified.',
    },
    'shuffle': {
        'parameters': {'n': {'required': 'when source is absent'}},
        'source': 'optional; rows along axis zero',
        'output': 'int64 permutation of range(n), or complete source rows in permuted order',
        'constraints': 'Returns a shuffled copy; never mutates the source.',
    },
    'bootstrap': {
        'parameters': {
            'n': {'required': 'when source is absent'},
            'resamples': {'default': 1},
            'sample_size': {'default': 'n'},
            'mode': {'default': 'ordinary', 'choices': ['ordinary', 'paired', 'cluster', 'block']},
            'groups': {'required': 'cluster mode only'},
            'block_length': {'required': 'block mode only'},
        },
        'source': 'optional; determines n only; apply emitted indices to source yourself',
        'output': '(resamples, sample_size) int64 observation indices',
        'constraints': 'ordinary/paired draw IID indices with replacement; paired means one shared index per complete observation. cluster samples whole equal-size clusters, preserving within-cluster row order; sample_size must divide by cluster size. block draws circular blocks, truncating the final block to sample_size. No statistic or confidence interval is inferred.',
    },
    'balanced_allocation': {
        'parameters': {'counts': {'required': True}, 'labels': {'default': 'range(len(counts))'}},
        'source': 'forbidden',
        'output': '(sum(counts),) treatment labels',
        'constraints': 'Nonnegative integer counts with positive total; unique homogeneous numeric or string labels. Exact counts, randomized assignment, no covariate balancing or clinical randomization claim.',
    },
    'split': {
        'parameters': {'n': {'required': 'when source is absent'}, 'counts': {'required': True}},
        'source': 'optional; determines n only',
        'output': '(n,) int64 permutation; consecutive slices of lengths counts are the partitions',
        'constraints': 'Counts sum exactly to n; each observation occurs once. No stratification, grouping or time-series assumptions are inferred.',
    },
    'sobol': {
        'parameters': {
            'n': {'required': True},
            'd': {'required': True},
            'scramble': {'default': True},
        },
        'source': 'forbidden',
        'output': '(n, d) float64 in [0,1)',
        'constraints': 'n is a positive power of two; d <= 21201. SciPy random_base2 uses bits=30, no skipped first point and no post-optimization. Scrambling consumes only the owned RNG; points are not IID.',
    },
    'halton': {
        'parameters': {
            'n': {'required': True},
            'd': {'required': True},
            'scramble': {'default': True},
        },
        'source': 'forbidden',
        'output': '(n, d) float64 in [0,1)',
        'constraints': 'Scrambled by default; no skipped first point or implicit optimization. High-dimensional striping is a scientific limitation, especially without scrambling; points are not IID.',
    },
    'latin_hypercube': {
        'parameters': {
            'n': {'required': True},
            'd': {'required': True},
            'scramble': {'default': True},
        },
        'source': 'forbidden',
        'output': '(n, d) float64 in [0,1)',
        'constraints': 'Strength-one Latin hypercube: one point per axis stratum. scramble=False centers points within bins but still randomizes bin permutations; no optimization is implicit.',
    },
    'poisson_disk': {
        'parameters': {
            'n': {'required': True},
            'd': {'required': True},
            'radius': {'default': 0.05},
            'max_trials': {'default': 'max(1000, 100*n)'},
        },
        'source': 'forbidden',
        'output': '(n, d) float64 in [0,1), or sampling_exhausted error',
        'constraints': 'Bounded sequential uniform dart-throwing with Euclidean minimum separation. Exact n or explicit failure; no partial result, relaxed radius, maximality or uniformity over feasible configurations. Trial budget and conservative n*d*max_trials work are preflighted.',
    },
    'korobov': {
        'parameters': {
            'n': {'required': True},
            'd': {'required': True},
            'generator': {'default': 'first coprime integer >=2; 1 when n<=2'},
            'shift': {'default': False},
        },
        'source': 'forbidden',
        'output': '(n, d) float64 in [0,1)',
        'constraints': 'Rank-one lattice with vector (1,g,g**2,...) modulo n; g coprime to n ensures Latin projections. Deterministic default is not a discrepancy-optimized generator. shift=True adds a random toroidal shift; points are not IID.',
    },
    'sudoku': {
        'parameters': {
            'n': {'required': True},
            'd': {'required': True},
            'boxes': {'default': 1},
            'scramble': {'default': True},
        },
        'source': 'forbidden',
        'output': '(n, d) float64 in [0,1)',
        'constraints': 'n divisible by boxes**d; every coarse cell has n/boxes**d points and every axis fine bin has one point. scramble=False centers bins but still randomizes their permutations.',
    },
    'stratified_sample': {
        'parameters': {
            'groups': {'required': True},
            'counts': {'required': True},
            'labels': {'default': 'first occurrence in groups'},
            'n': {'default': 'len(groups), matching source rows'},
            'replace': {'default': False},
        },
        'source': 'optional; establishes observation count only',
        'output': '(sum(counts),) int64 indices, concatenated in resolved label order',
        'constraints': 'Homogeneous integer or string group labels; labels must cover every observed stratum exactly once. Nonnegative counts, including zero; without replacement every count must fit its stratum. Uniform sampling within each stratum, no implicit population weights.',
    },
    'stratified_split': {
        'parameters': {
            'groups': {'required': True},
            'counts': {'required': True},
            'labels': {'default': 'first occurrence in groups'},
            'n': {'default': 'len(groups), matching source rows'},
        },
        'source': 'optional; establishes observation count only',
        'output': '(n,) int64 indices, consecutive partitions have counts-column totals',
        'constraints': 'Counts matrix rows follow resolved label order and columns are partitions; each row sum must equal its stratum population. Exact per-stratum counts, disjoint partitions, exhaustive observation coverage. Observations randomized within each partition; no group/time constraints are inferred.',
    },
    'antithetic': {
        'parameters': {
            'n': {'required': True},
            'd': {'required': True},
            'distribution': {'default': 'normal', 'choices': ['normal', 'uniform']},
            'loc': {'default': 0.0, 'condition': 'normal only'},
            'scale': {'default': 1.0, 'condition': 'normal only'},
            'low': {'default': 0.0, 'condition': 'uniform only'},
            'high': {'default': 1.0, 'condition': 'uniform only'},
        },
        'source': 'forbidden',
        'output': '(n, d) float64; paired rows i and i+n/2',
        'constraints': 'Positive even n; normal scale nonnegative; uniform finite low<high and representable interior. First-half variates and reflected second-half variates are dependent with the declared marginal law, subject to float64 rounding. Uniform uses complementary unit variates and maps rounded endpoints to their nearest interior float; points lie strictly between bounds. Variance reduction depends on the integrand and is not guaranteed.',
    },
    'distribution': {
        'parameters': {
            'distribution': {'required': True},
            'size': {'default': 1},
            'named_parameters': {'description': 'exact registered distribution parameters only'},
        },
        'source': 'forbidden',
        'output': 'size shape followed by registered event dimensions',
        'constraints': 'Explicit SciPy registry, finite scalar/array parameters, strict domain validation, no arbitrary object lookup. Heavy-tailed draws may fail the finite-output contract. Distribution transforms are pinned by the recorded environment, not universally bit-stable.',
    },
}


def catalog() -> dict:
    """Return a JSON-compatible catalog generated from the operation registry."""
    return {
        'schema_version': 'chances.operations.v1',
        'operations': deepcopy(_OPERATIONS),
        'distributions': distribution_catalog(),
        'resource_limits': deepcopy(_DEFAULT_LIMITS),
        'size_semantics': 'size is a nonnegative integer or list of nonnegative dimensions; [] means a scalar; zero-sized outputs are allowed for shape-based draws.',
        'resource_semantics': 'Conservative output/scratch and work estimates are preflighted. max_work is an algorithmic planning bound, not a wall-clock timeout for SciPy numerical routines.',
    }


def _limits(limits: dict) -> dict:
    result = dict(_DEFAULT_LIMITS)
    for key, value in limits.items():
        if key not in result:
            raise ChancesError('UNKNOWN_PARAMETERS', 'Unknown resource limit', {'parameter': key})
        result[key] = integer(value, key, 1)
    return result


def _resource(
    shape: tuple[int, ...],
    limits: dict,
    *,
    itemsize: int = 8,
    scratch: int = 3,
    work: int | None = None,
    extra_bytes: int = 0,
) -> None:
    if len(shape) > 16:
        fail('Output supports at most 16 dimensions', parameter='size')
    count = math.prod(shape)
    estimates = {
        'max_values': count,
        'max_bytes': count * itemsize * scratch + extra_bytes,
        'max_work': count if work is None else work,
    }
    for key, required in estimates.items():
        if required > limits[key]:
            raise ChancesError(
                'RESOURCE_LIMIT',
                f'{key} would be exceeded',
                {'limit': key, 'required': required, 'allowed': limits[key]},
            )


def _unknown(parameters: dict, allowed: set[str]) -> None:
    extras = set(parameters) - allowed
    if extras:
        raise ChancesError(
            'UNKNOWN_PARAMETERS', 'Unknown operation parameter', {'parameters': sorted(extras)}
        )


def _required(parameters: dict, key: str) -> object:
    if key not in parameters:
        fail(f'{key} is required', parameter=key)
    return parameters[key]


def _population(parameters: dict, source: np.ndarray | None) -> int:
    if source is None:
        return integer(_required(parameters, 'n'), 'n', 1)
    if not isinstance(source, np.ndarray) or source.ndim < 1 or source.shape[0] == 0:
        fail('source must have a nonempty observation axis', parameter='source')
    n = source.shape[0]
    if 'n' in parameters and integer(parameters['n'], 'n', 1) != n:
        fail('n must match the source observation count', parameter='n')
    return n


def _counts(value: object) -> list[int]:
    if not isinstance(value, list) or not value:
        fail('counts must be a nonempty list of nonnegative integers', parameter='counts')
    counts = [integer(v, 'counts', 0) for v in value]
    if sum(counts) == 0:
        fail('counts must have a positive total', parameter='counts')
    return counts


def _labels(value: object, n: int) -> list:
    if value is None:
        return list(range(n))
    if not isinstance(value, list) or len(value) != n:
        fail('labels must have one entry per count', parameter='labels')
    if all(type(v) is str for v in value):
        labels = value[:]
    elif all(
        isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_)) for v in value
    ):
        labels = [integer(v, 'labels') for v in value]
    elif all(isinstance(v, (float, np.floating)) for v in value):
        labels = [number(v, 'labels') for v in value]
    else:
        fail('labels must be homogeneous strings, integers or finite floats', parameter='labels')
    if len(set(labels)) != n:
        fail('labels must be unique', parameter='labels')
    return labels


def _cluster_rows(groups: list) -> list[list[int]]:
    rows: dict[object, list[int]] = {}
    for index, label in enumerate(groups):
        rows.setdefault(label, []).append(index)
    return list(rows.values())


def resolve_operation(name: str, parameters: dict, source: np.ndarray | None, limits: dict) -> dict:
    """Resolve deterministic defaults, validate domains and preflight resources."""
    if not isinstance(name, str) or name not in _OPERATIONS:
        raise ChancesError('UNKNOWN_OPERATION', 'Operation is not registered', {'operation': name})
    if not isinstance(parameters, dict) or any(type(key) is not str for key in parameters):
        fail('parameters must be an object with string keys', parameter='parameters')
    limits = _limits(limits)
    if source is not None and name not in (
        'choice',
        'permutation',
        'shuffle',
        'bootstrap',
        'split',
        'stratified_sample',
        'stratified_split',
    ):
        fail(f'{name} does not accept source observations', parameter='source')
    if name == 'distribution':
        return resolve_distribution(deepcopy(parameters), limits)
    if name in ('integers', 'uniform', 'normal'):
        return _resolve_draw(name, parameters, limits)
    if name in ('choice', 'permutation', 'shuffle', 'bootstrap', 'split'):
        return _resolve_population(name, parameters, source, limits)
    if name in ('stratified_sample', 'stratified_split'):
        return _resolve_stratified(name, parameters, source, limits)
    if name == 'antithetic':
        return _resolve_antithetic(parameters, limits)
    if name == 'balanced_allocation':
        return _resolve_allocation(parameters, limits)
    return _resolve_design(name, parameters, limits)


def _resolve_draw(name: str, parameters: dict, limits: dict) -> dict:
    out: dict = {}
    keys = {
        'integers': {'low', 'high', 'size', 'endpoint', 'dtype'},
        'uniform': {'low', 'high', 'size'},
        'normal': {'loc', 'scale', 'size'},
    }[name]
    _unknown(parameters, keys)
    out['size'] = deepcopy(parameters.get('size', 1))
    shape = size_shape(out['size'])
    if name == 'integers':
        # NumPy supports an exclusive high of dtype.max+1.
        low, high = parameters.get('low', 0), _required(parameters, 'high')
        for key, value in [('low', low), ('high', high)]:
            if type(value) is not int:
                fail(f'{key} must be an integer', parameter=key)
        out.update(
            low=low, high=high, endpoint=boolean(parameters.get('endpoint', False), 'endpoint')
        )
        dtype = parameters.get('dtype', 'int64')
        if dtype not in ('int32', 'int64', 'uint32', 'uint64'):
            fail('dtype must be a registered integer type', parameter='dtype')
        out['dtype'] = dtype
        bounds = np.iinfo(dtype)
        maximum = high if out['endpoint'] else high - 1
        if low > maximum or low < bounds.min or maximum > bounds.max:
            fail('Integer bounds are empty or exceed the declared dtype', parameter='high')
        _resource(shape, limits, itemsize=np.dtype(dtype).itemsize)
    elif name == 'uniform':
        out['low'] = number(parameters.get('low', 0.0), 'low')
        out['high'] = number(parameters.get('high', 1.0), 'high')
        if out['high'] <= out['low'] or not math.isfinite(out['high'] - out['low']):
            fail('uniform requires low < high and a finite interval width')
        _resource(shape, limits)
    else:
        out['loc'] = number(parameters.get('loc', 0.0), 'loc')
        out['scale'] = number(parameters.get('scale', 1.0), 'scale', minimum=0)
        _resource(shape, limits)
    return out


def _resolve_population(
    name: str, parameters: dict, source: np.ndarray | None, limits: dict
) -> dict:
    out: dict = {}
    keys = {
        'choice': {'n', 'size', 'replace', 'p'},
        'permutation': {'n'},
        'shuffle': {'n'},
        'bootstrap': {'n', 'resamples', 'sample_size', 'mode', 'groups', 'block_length'},
        'split': {'n', 'counts'},
    }[name]
    _unknown(parameters, keys)
    n = _population(parameters, source)
    out['n'] = n
    tail = () if source is None else source.shape[1:]
    itemsize = 8 if source is None else source.dtype.itemsize
    if name == 'choice':
        out['size'] = deepcopy(parameters.get('size', 1))
        shape = size_shape(out['size'])
        draws = math.prod(shape)
        out['replace'] = boolean(parameters.get('replace', True), 'replace')
        out['p'] = None if parameters.get('p') is None else probabilities(parameters['p'], n)
        if not out['replace'] and (
            draws > n or (out['p'] is not None and draws > sum(p > 0 for p in out['p']))
        ):
            fail('Without-replacement sample exceeds eligible population', parameter='size')
        _resource(shape + tail, limits, itemsize=itemsize, work=max(draws, n), extra_bytes=n * 24)
    elif name == 'bootstrap':
        return _resolve_bootstrap(parameters, out, limits)
    elif name == 'split':
        out['counts'] = _counts(_required(parameters, 'counts'))
        if sum(out['counts']) != n:
            fail('split counts must sum exactly to n', parameter='counts')
        _resource((n,), limits, extra_bytes=len(out['counts']) * 8)
    else:
        _resource((n, *tail), limits, itemsize=itemsize, extra_bytes=n * 8)
    return out


def _resolve_stratified(
    name: str, parameters: dict, source: np.ndarray | None, limits: dict
) -> dict:
    out: dict = {}
    allowed = {'groups', 'counts', 'labels', 'n'}
    if name == 'stratified_sample':
        allowed.add('replace')
    _unknown(parameters, allowed)
    groups, labels, rows = _resolve_strata(parameters, source, limits)
    out.update(n=len(groups), groups=groups, labels=labels)
    raw_counts = _required(parameters, 'counts')
    if not isinstance(raw_counts, list) or len(raw_counts) != len(labels):
        fail('counts must have one row or entry per resolved label', parameter='counts')
    if name == 'stratified_sample':
        counts = [integer(value, 'counts', 0) for value in raw_counts]
        out['replace'] = boolean(parameters.get('replace', False), 'replace')
        if not out['replace'] and any(count > len(row) for count, row in zip(counts, rows)):
            fail('Without-replacement stratum count exceeds its population', parameter='counts')
        out['counts'] = counts
        values = sum(counts)
        _resource(
            (values,),
            limits,
            scratch=4,
            work=8 * (values + len(groups)),
            extra_bytes=len(groups) * 64,
        )
    else:
        if not all(isinstance(row, list) and row for row in raw_counts):
            fail('counts must be a nonempty matrix', parameter='counts')
        partitions = len(raw_counts[0])
        if any(len(row) != partitions for row in raw_counts):
            fail('Every counts row must have the same number of partitions', parameter='counts')
        counts = [[integer(value, 'counts', 0) for value in row] for row in raw_counts]
        if any(sum(count) != len(rows[index]) for index, count in enumerate(counts)):
            fail('Each counts row must sum to its stratum population', parameter='counts')
        out['counts'] = counts
        _resource(
            (len(groups),),
            limits,
            scratch=6,
            work=len(groups) * 16 + len(labels) * partitions * 8,
            extra_bytes=len(groups) * 64 + len(labels) * partitions * 256,
        )
    return out


def _resolve_antithetic(parameters: dict, limits: dict) -> dict:
    out: dict = {}
    law = parameters.get('distribution', 'normal')
    if law not in ('normal', 'uniform'):
        fail('Antithetic distribution must be normal or uniform', parameter='distribution')
    allowed = {
        'n',
        'd',
        'distribution',
        *({'loc', 'scale'} if law == 'normal' else {'low', 'high'}),
    }
    _unknown(parameters, allowed)
    n = integer(_required(parameters, 'n'), 'n', 2)
    d = integer(_required(parameters, 'd'), 'd', 1)
    if n % 2:
        fail('Antithetic n must be even', parameter='n')
    out.update(n=n, d=d, distribution=law)
    if law == 'normal':
        out['loc'] = number(parameters.get('loc', 0.0), 'loc')
        out['scale'] = number(parameters.get('scale', 1.0), 'scale', minimum=0)
    else:
        out['low'] = number(parameters.get('low', 0.0), 'low')
        out['high'] = number(parameters.get('high', 1.0), 'high')
        if out['high'] <= out['low'] or not math.isfinite(out['high'] - out['low']):
            fail('Antithetic uniform requires low<high and finite width')
        if np.nextafter(out['low'], out['high']) >= out['high']:
            fail('Antithetic uniform requires a representable interior float')
    _resource((n, d), limits, scratch=5, work=n * d * 8)
    return out


def _resolve_allocation(parameters: dict, limits: dict) -> dict:
    out: dict = {}
    _unknown(parameters, {'counts', 'labels'})
    out['counts'] = _counts(_required(parameters, 'counts'))
    out['labels'] = _labels(parameters.get('labels'), len(out['counts']))
    itemsize = np.asarray(out['labels']).dtype.itemsize
    _resource(
        (sum(out['counts']),), limits, itemsize=itemsize, extra_bytes=len(out['counts']) * itemsize
    )
    return out


def _resolve_design(name: str, parameters: dict, limits: dict) -> dict:
    out: dict = {}
    keys = {
        'sobol': {'n', 'd', 'scramble'},
        'halton': {'n', 'd', 'scramble'},
        'latin_hypercube': {'n', 'd', 'scramble'},
        'sudoku': {'n', 'd', 'scramble', 'boxes'},
        'korobov': {'n', 'd', 'generator', 'shift'},
        'poisson_disk': {'n', 'd', 'radius', 'max_trials'},
    }[name]
    _unknown(parameters, keys)
    n = integer(_required(parameters, 'n'), 'n', 1)
    d = integer(_required(parameters, 'd'), 'd', 1)
    out.update(n=n, d=d)
    _resource((n, d), limits, scratch=5, work=n * d * 8)
    if name in ('sobol', 'halton', 'latin_hypercube', 'sudoku'):
        out['scramble'] = boolean(parameters.get('scramble', True), 'scramble')
    if name == 'sobol':
        _resolve_sobol(out, limits)
    elif name == 'halton':
        # Scramble tables cover floating precision for every prime base;
        # sum-of-bases storage grows quadratically with dimension.
        _resource((n, d), limits, scratch=5, work=n * d * 64 + d * d * 32, extra_bytes=d * d * 256)
    elif name == 'poisson_disk':
        _resolve_poisson_disk(parameters, out, limits)
    elif name == 'korobov':
        _resolve_korobov(parameters, out)
    elif name == 'sudoku':
        _resolve_sudoku(parameters, out, limits)
    return out


def operation_output(
    name: str, parameters: dict, source: np.ndarray | None
) -> tuple[tuple[int, ...], np.dtype]:
    """Describe a resolved operation's exact array shape and dtype."""
    if name == 'distribution':
        return distribution_output(parameters)
    if name == 'integers':
        return size_shape(parameters['size']), np.dtype(parameters['dtype'])
    if name in ('uniform', 'normal'):
        return size_shape(parameters['size']), np.dtype('float64')
    if name == 'choice':
        return size_shape(parameters['size']) + (
            () if source is None else source.shape[1:]
        ), np.dtype('int64') if source is None else source.dtype
    if name in ('permutation', 'shuffle'):
        return (parameters['n'],) if source is None else source.shape, np.dtype(
            'int64'
        ) if source is None else source.dtype
    if name == 'bootstrap':
        return (parameters['resamples'], parameters['sample_size']), np.dtype('int64')
    if name in ('split', 'stratified_split'):
        return (parameters['n'],), np.dtype('int64')
    if name == 'stratified_sample':
        return (sum(parameters['counts']),), np.dtype('int64')
    if name == 'balanced_allocation':
        return (sum(parameters['counts']),), np.asarray(parameters['labels']).dtype
    return (parameters['n'], parameters['d']), np.dtype('float64')


def execute_operation(
    name: str, parameters: dict, rng: np.random.Generator, source: np.ndarray | None
) -> np.ndarray:
    """Execute only a resolved operation, consuming the supplied local RNG."""
    p = parameters
    if name == 'distribution':
        return execute_distribution(p, rng)
    if name in ('integers', 'uniform', 'normal'):
        return _execute_draw(name, p, rng)
    if name in ('choice', 'permutation', 'shuffle', 'split'):
        return _execute_selection(name, p, rng, source)
    if name == 'bootstrap':
        return _execute_bootstrap(p, rng)
    if name in ('stratified_sample', 'stratified_split'):
        return _execute_stratified(name, p, rng)
    if name == 'antithetic':
        return _execute_antithetic(p, rng)
    if name == 'balanced_allocation':
        return _execute_allocation(p, rng)
    if name in ('sobol', 'halton', 'latin_hypercube', 'korobov', 'sudoku', 'poisson_disk'):
        return _execute_design(name, p, rng)
    raise ChancesError('UNKNOWN_OPERATION', 'Operation is not registered', {'operation': name})


def _execute_draw(name: str, p: dict, rng: np.random.Generator) -> np.ndarray:
    if name == 'integers':
        return rng.integers(
            p['low'],
            p['high'],
            size=size_shape(p['size']),
            endpoint=p['endpoint'],
            dtype=np.dtype(p['dtype']),
        )
    if name == 'uniform':
        out = rng.uniform(p['low'], p['high'], size=size_shape(p['size']))
        np.minimum(out, np.nextafter(p['high'], p['low']), out=out)
        return out
    if name == 'normal':
        return rng.normal(p['loc'], p['scale'], size=size_shape(p['size']))
    raise ChancesError('UNKNOWN_OPERATION', 'Operation is not registered', {'operation': name})


def _execute_selection(
    name: str, p: dict, rng: np.random.Generator, source: np.ndarray | None
) -> np.ndarray:
    if name == 'choice':
        indices = rng.choice(p['n'], size=size_shape(p['size']), replace=p['replace'], p=p['p'])
        return np.asarray(indices, dtype=np.int64) if source is None else source[indices]
    if name in ('permutation', 'shuffle', 'split'):
        indices = rng.permutation(p['n'])
        return (
            np.asarray(indices, dtype=np.int64)
            if source is None or name == 'split'
            else source[indices]
        )
    raise ChancesError('UNKNOWN_OPERATION', 'Operation is not registered', {'operation': name})


def _execute_design(name: str, p: dict, rng: np.random.Generator) -> np.ndarray:
    if name == 'sobol':
        return qmc.Sobol(p['d'], scramble=p['scramble'], bits=30, rng=rng).random_base2(
            int(math.log2(p['n']))
        )
    if name == 'halton':
        return qmc.Halton(p['d'], scramble=p['scramble'], rng=rng).random(p['n'])
    if name == 'latin_hypercube':
        return qmc.LatinHypercube(p['d'], scramble=p['scramble'], strength=1, rng=rng).random(
            p['n']
        )
    if name == 'korobov':
        return _execute_korobov(p, rng)
    if name == 'sudoku':
        return _execute_sudoku(p, rng)
    if name == 'poisson_disk':
        return _execute_poisson_disk(p, rng)
    raise ChancesError('UNKNOWN_OPERATION', 'Operation is not registered', {'operation': name})


def _execute_bootstrap(p: dict, rng: np.random.Generator) -> np.ndarray:
    shape = (p['resamples'], p['sample_size'])
    if p['mode'] in ('ordinary', 'paired'):
        return rng.integers(0, p['n'], size=shape, dtype=np.int64)
    if p['mode'] == 'cluster':
        rows = np.array(_cluster_rows(p['groups']), dtype=np.int64)
        indices = rng.integers(len(rows), size=(p['resamples'], p['sample_size'] // rows.shape[1]))
        return rows[indices].reshape(shape)
    length = p['block_length']
    starts = rng.integers(p['n'], size=(p['resamples'], math.ceil(p['sample_size'] / length), 1))
    blocks = (starts + np.arange(length)) % p['n']
    return blocks.reshape(p['resamples'], -1)[:, : p['sample_size']].copy()


def _execute_stratified(name: str, p: dict, rng: np.random.Generator) -> np.ndarray:
    rows = _stratum_rows(p['groups'], p['labels'])
    if name == 'stratified_sample':
        sampled = [
            rng.choice(row, size=count, replace=p['replace'])
            for row, count in zip(rows, p['counts'])
        ]
        return np.concatenate(sampled).astype(np.int64, copy=False)
    partitions: list[list[np.ndarray]] = [[] for _ in p['counts'][0]]
    for row, counts in zip(rows, p['counts']):
        shuffled = rng.permutation(row)
        offset = 0
        for partition, count in enumerate(counts):
            partitions[partition].append(shuffled[offset : offset + count])
            offset += count
    out = []
    for partition in partitions:
        indices = np.concatenate(partition)
        out.append(rng.permutation(indices))
    return np.concatenate(out).astype(np.int64, copy=False)


def _execute_antithetic(p: dict, rng: np.random.Generator) -> np.ndarray:
    half_shape = (p['n'] // 2, p['d'])
    if p['distribution'] == 'normal':
        centered = rng.standard_normal(half_shape) * p['scale']
        first, second = p['loc'] + centered, p['loc'] - centered
    else:
        unit = rng.random(half_shape)
        width = p['high'] - p['low']
        first, second = p['low'] + width * unit, p['low'] + width * (1.0 - unit)
        lower, upper = np.nextafter(p['low'], p['high']), np.nextafter(p['high'], p['low'])
        np.clip(first, lower, upper, out=first)
        np.clip(second, lower, upper, out=second)
    return np.concatenate((first, second), axis=0)


def _execute_allocation(p: dict, rng: np.random.Generator) -> np.ndarray:
    values = np.repeat(np.asarray(p['labels']), p['counts'])
    rng.shuffle(values)
    return values


def _execute_korobov(p: dict, rng: np.random.Generator) -> np.ndarray:
    n, d, g = p['n'], p['d'], p['generator']
    powers = np.array([pow(g, axis, n) for axis in range(d)], dtype=np.int64)
    ranks = np.arange(n, dtype=np.int64)[:, None] * powers[None, :] % n
    out = ranks.astype(np.float64) / n
    if p['shift']:
        out = (out + rng.random(d)) % 1.0
    return out


def _execute_sudoku(p: dict, rng: np.random.Generator) -> np.ndarray:
    n, d, boxes = p['n'], p['d'], p['boxes']
    cells = boxes**d
    codes = np.arange(cells, dtype=np.int64)
    cell_axes = np.empty((cells, d), dtype=np.int64)
    divisor = 1
    for axis in range(d):
        cell_axes[:, axis] = codes // divisor % boxes
        divisor *= boxes
    cell_axes = np.tile(cell_axes, (n // cells, 1))
    ranks = np.empty((n, d), dtype=np.int64)
    bins_per_box = n // boxes
    for axis in range(d):
        for box in range(boxes):
            rows = np.flatnonzero(cell_axes[:, axis] == box)
            ranks[rows, axis] = box * bins_per_box + rng.permutation(bins_per_box)
    offsets = rng.random((n, d)) if p['scramble'] else 0.5
    out = (ranks + offsets) / n
    return out[rng.permutation(n)]


def _execute_poisson_disk(p: dict, rng: np.random.Generator) -> np.ndarray:
    points = np.empty((p['n'], p['d']), dtype=np.float64)
    accepted = 0
    radius_squared = p['radius'] ** 2
    for _ in range(p['max_trials']):
        candidate = rng.random(p['d'])
        delta = points[:accepted] - candidate
        if accepted == 0 or np.all(np.einsum('ij,ij->i', delta, delta) >= radius_squared):
            points[accepted] = candidate
            accepted += 1
            if accepted == p['n']:
                return points
    raise ChancesError(
        'SAMPLING_EXHAUSTED',
        'Poisson disk trial budget exhausted',
        {
            'accepted': accepted,
            'requested': p['n'],
            'max_trials': p['max_trials'],
            'radius': p['radius'],
        },
    )


def _stratum_rows(groups: list, labels: list) -> list[np.ndarray]:
    by_label = {label: [] for label in labels}
    for index, label in enumerate(groups):
        by_label[label].append(index)
    return [np.asarray(by_label[label], dtype=np.int64) for label in labels]


def _resolve_strata(
    parameters: dict, source: np.ndarray | None, limits: dict
) -> tuple[list, list, list[np.ndarray]]:
    groups = _required(parameters, 'groups')
    if not isinstance(groups, list) or not groups:
        fail('groups must be a nonempty list', parameter='groups')
    if all(type(label) is str for label in groups):
        groups = groups[:]
    elif all(type(label) is int for label in groups):
        groups = [integer(label, 'groups') for label in groups]
    else:
        fail('groups must contain homogeneous string or integer labels', parameter='groups')
    n = len(groups)
    if (source is not None and _population(parameters, source) != n) or (
        'n' in parameters and integer(parameters['n'], 'n', 1) != n
    ):
        fail('groups must identify every population observation', parameter='groups')
    first_occurrence = list(dict.fromkeys(groups))
    labels = parameters.get('labels', first_occurrence)
    if not isinstance(labels, list):
        fail('labels must be a list of stratum labels', parameter='labels')
    labels = _labels(labels, len(first_occurrence))
    if type(labels[0]) is not type(groups[0]) or set(labels) != set(first_occurrence):
        fail('labels must cover every observed stratum exactly once', parameter='labels')
    _resource((n,), limits, scratch=8, work=n * 8 + len(labels) * 8)
    return groups, labels, _stratum_rows(groups, labels)


def operation_postconditions(name: str, parameters: dict, source: np.ndarray | None) -> dict:
    """JSON-compatible exact output shape, dtype and declared support metadata."""
    shape, dtype = operation_output(name, parameters, source)
    out: dict[str, object] = {'shape': list(shape), 'dtype': dtype.str, 'finite': True}
    p = parameters
    out['support'] = _operation_support(name, p, source)
    if name == 'antithetic':
        out['dependence'] = {'kind': 'antithetic_pairs', 'paired_offset': p['n'] // 2, 'iid': False}
    elif name in ('sobol', 'halton', 'latin_hypercube', 'korobov', 'sudoku', 'poisson_disk'):
        out['dependence'] = {'kind': 'design', 'iid': False}
    if name in ('stratified_sample', 'stratified_split'):
        out['stratification'] = {
            'labels': p['labels'][:],
            'counts': deepcopy(p['counts']),
            'ordering': 'stratum_major' if name == 'stratified_sample' else 'partition_major',
            'replace': p['replace'] if name == 'stratified_sample' else False,
        }
    return out


def _resolve_bootstrap(parameters: dict, out: dict, limits: dict) -> dict:
    n = out['n']
    out['resamples'] = integer(parameters.get('resamples', 1), 'resamples', 1)
    out['sample_size'] = integer(parameters.get('sample_size', n), 'sample_size', 1)
    mode = parameters.get('mode', 'ordinary')
    if mode not in ('ordinary', 'paired', 'cluster', 'block'):
        fail('Unknown bootstrap mode', parameter='mode')
    out['mode'] = mode
    if (mode != 'cluster' and 'groups' in parameters) or (
        mode != 'block' and 'block_length' in parameters
    ):
        fail('groups and block_length must match their declared bootstrap mode')
    if mode == 'cluster':
        _resolve_cluster(parameters, out)
    elif mode == 'block':
        out['block_length'] = integer(_required(parameters, 'block_length'), 'block_length', 1)
        if out['block_length'] > n:
            fail('block_length must not exceed the observation count', parameter='block_length')
    shape = (out['resamples'], out['sample_size'])
    work = math.prod(shape) + n
    extra = n * 24
    if mode == 'block':
        padded = (
            out['resamples']
            * math.ceil(out['sample_size'] / out['block_length'])
            * out['block_length']
        )
        extra += padded * 24
        work += padded
    _resource(shape, limits, scratch=4, work=work, extra_bytes=extra)
    return out


def _resolve_cluster(parameters: dict, out: dict) -> None:
    n = out['n']
    groups = _required(parameters, 'groups')
    # Labels may repeat, unlike treatment labels.
    if not isinstance(groups, list) or len(groups) != n:
        fail('groups must identify every population observation', parameter='groups')
    if all(type(v) is str for v in groups):
        out['groups'] = groups[:]
    elif all(type(v) is int for v in groups):
        out['groups'] = [integer(v, 'groups') for v in groups]
    else:
        fail('groups must contain homogeneous string or integer labels', parameter='groups')
    rows = _cluster_rows(out['groups'])
    cluster_size = len(rows[0])
    if any(len(row) != cluster_size for row in rows) or out['sample_size'] % cluster_size:
        fail(
            'Cluster bootstrap requires equal cluster sizes and sample_size divisible by cluster size'
        )


def _resolve_sudoku(parameters: dict, out: dict, limits: dict) -> None:
    n, d = out['n'], out['d']
    boxes = integer(parameters.get('boxes', 1), 'boxes', 1)
    # Avoid constructing arbitrarily large Python integers from input.
    cells = 1
    for _ in range(d):
        cells *= boxes
        if cells > n:
            fail('n must be divisible by boxes**d', parameter='boxes')
    if n % cells:
        fail('n must be divisible by boxes**d', parameter='boxes')
    out['boxes'] = boxes
    _resource((n, d), limits, scratch=6, work=n * d * (boxes + 8))


def _resolve_korobov(parameters: dict, out: dict) -> None:
    n = out['n']
    if 'generator' in parameters:
        generator = integer(parameters['generator'], 'generator', 1)
    else:
        generator = 1 if n <= 2 else 2
        while math.gcd(generator, n) != 1:
            generator += 1
    if math.gcd(generator, n) != 1:
        fail('generator must be coprime to n', parameter='generator')
    out['generator'] = generator
    out['shift'] = boolean(parameters.get('shift', False), 'shift')
    # Integer multiplication is safe under the output resource cap.
    if n * n >= 2**63:
        fail('n is too large for safe lattice arithmetic', parameter='n')


def _resolve_poisson_disk(parameters: dict, out: dict, limits: dict) -> None:
    n, d = out['n'], out['d']
    out['radius'] = number(parameters.get('radius', 0.05), 'radius', positive=True)
    out['max_trials'] = integer(parameters.get('max_trials', max(1000, 100 * n)), 'max_trials', 1)
    if out['max_trials'] < n:
        fail('max_trials must be at least n', parameter='max_trials')
    if out['radius'] > math.sqrt(d) or (n > 1 and out['radius'] >= math.sqrt(d)):
        fail('radius makes the requested count infeasible in the unit cube', parameter='radius')
    _resource((n, d), limits, scratch=5, work=out['max_trials'] * n * d * 4)


def _resolve_sobol(out: dict, limits: dict) -> None:
    n, d = out['n'], out['d']
    if n & (n - 1) or n > 2**30:
        fail('Sobol n must be a positive power of two no larger than 2**30', parameter='n')
    if d > 21201:
        fail('Sobol supports at most 21201 dimensions', parameter='d')
    _resource(
        (n, d),
        limits,
        scratch=5,
        work=n * d + d * 30 * 30,
        extra_bytes=d * 30 * 30 * 8 if out['scramble'] else d * 30 * 8,
    )


def _operation_support(name: str, p: dict, source: np.ndarray | None) -> dict:
    out: dict = {}
    if name == 'distribution':
        out['support'] = distribution_support(p)
    elif name == 'integers':
        out['support'] = {
            'kind': 'interval',
            'low': p['low'],
            'high': p['high'],
            'lower_inclusive': True,
            'upper_inclusive': p['endpoint'],
            'integral': True,
        }
    elif name == 'uniform' or (name == 'antithetic' and p['distribution'] == 'uniform'):
        out['support'] = {
            'kind': 'interval',
            'low': p['low'],
            'high': p['high'],
            'lower_inclusive': name == 'uniform',
            'upper_inclusive': False,
            'integral': False,
        }
    elif name in ('normal', 'antithetic'):
        out['support'] = {
            'kind': 'interval',
            'low': p['loc'] if p['scale'] == 0 else None,
            'high': p['loc'] if p['scale'] == 0 else None,
            'lower_inclusive': True,
            'upper_inclusive': True,
            'integral': False,
        }
    elif name in ('choice', 'permutation', 'shuffle') and source is not None:
        out['support'] = {'kind': 'source_rows', 'axis': 0}
    elif name in (
        'choice',
        'permutation',
        'shuffle',
        'bootstrap',
        'split',
        'stratified_sample',
        'stratified_split',
    ):
        out['support'] = {
            'kind': 'interval',
            'low': 0,
            'high': p['n'],
            'lower_inclusive': True,
            'upper_inclusive': False,
            'integral': True,
        }
    elif name == 'balanced_allocation':
        out['support'] = {'kind': 'finite_values', 'values': p['labels'][:]}
    else:
        out['support'] = {
            'kind': 'interval',
            'low': 0.0,
            'high': 1.0,
            'lower_inclusive': True,
            'upper_inclusive': False,
            'integral': False,
        }
    return out['support']
