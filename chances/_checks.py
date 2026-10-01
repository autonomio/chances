"""Output domains and structural contracts, checked before publication or use."""

from __future__ import annotations

import math

import numpy as np

from ._errors import ChancesError
from ._operations import operation_output, operation_postconditions


def _require(condition: object, operation: str, message: str) -> None:
    if not bool(condition):
        raise ChancesError('CONTRACT_VIOLATION', message, {'operation': operation})


def preflight_checks(operation: str, p: dict, source: np.ndarray | None, limits: dict) -> None:
    """Account for sorting and structural verification beyond backend execution."""
    shape, dtype = operation_output(operation, p, source)
    values = math.prod(shape)
    work = values * 4
    unique = (
        operation in ('permutation', 'shuffle', 'split', 'stratified_split')
        or (operation == 'choice' and not p['replace'])
        or (operation == 'stratified_sample' and not p['replace'])
    )
    if unique:
        count = p['n'] if operation in ('permutation', 'shuffle') else values
        work += (
            count
            * max(1, count.bit_length())
            * max(
                1,
                math.prod(source.shape[1:])
                if source is not None and operation in ('permutation', 'shuffle', 'choice')
                else 1,
            )
        )
    if operation in ('sobol', 'latin_hypercube', 'korobov', 'sudoku'):
        work += values * max(1, p['n'].bit_length())
    if operation == 'distribution':
        name = p['distribution']
        if name == 'mixture':
            work += values * sum(w > 0 for w in p['weights']) * 4
        elif name in ('wishart', 'invwishart'):
            work += math.prod(shape[:-2]) * shape[-1] ** 3 * 4
        elif name == 'empirical':
            work += (values + len(p['values'])) * max(1, len(p['values']).bit_length())
    bytes_needed = values * dtype.itemsize * 4 + (source.nbytes * 4 if source is not None else 0)
    if bytes_needed > limits['max_bytes']:
        raise ChancesError(
            'RESOURCE_LIMIT',
            'Output verification and source snapshots exceed the declared byte budget.',
            {'required': bytes_needed, 'allowed': limits['max_bytes'], 'phase': 'postconditions'},
        )
    if work > limits['max_work']:
        raise ChancesError(
            'RESOURCE_LIMIT',
            'Output verification exceeds the declared work budget.',
            {'required': work, 'allowed': limits['max_work'], 'phase': 'postconditions'},
        )


def check_output(operation: str, p: dict, source: np.ndarray | None, data: np.ndarray) -> None:
    shape, dtype = operation_output(operation, p, source)
    _require(
        data.shape == shape,
        operation,
        'Output shape differs from the resolved scientific contract.',
    )
    _require(
        data.dtype == dtype,
        operation,
        'Output dtype differs from the resolved scientific contract.',
    )
    if data.size == 0:
        return
    support = operation_postconditions(operation, p, source)['support']
    _require(
        _in_support(support, data, source),
        operation,
        'Output violates its declared mathematical support.',
    )
    if operation in ('permutation', 'shuffle'):
        _check_permutation(operation, p, source, data)
    elif (
        operation in ('split', 'stratified_split')
        or (operation == 'choice' and not p['replace'])
        or (operation == 'stratified_sample' and not p['replace'])
    ):
        _check_without_replacement(operation, p, source, data)
    handler = _STRUCTURAL_CHECKS.get(operation)
    if handler is not None:
        handler(operation, p, source, data)


def _check_permutation(
    operation: str, p: dict, source: np.ndarray | None, data: np.ndarray
) -> None:
    if source is None:
        _require(
            np.unique(data).size == p['n'],
            operation,
            'Permutation must contain each population index once.',
        )
    else:
        # Fixed-width row bytes retain complete observations, including strings.
        actual = _row_counts(data)
        expected = _row_counts(source)
        _require(
            np.array_equal(actual[0], expected[0]) and np.array_equal(actual[1], expected[1]),
            operation,
            'Permutation changed complete source observations.',
        )


def _check_without_replacement(
    operation: str, p: dict, source: np.ndarray | None, data: np.ndarray
) -> None:
    if source is None or operation in ('split', 'stratified_split', 'stratified_sample'):
        _require(
            np.unique(data).size == data.size,
            operation,
            'Without-replacement output repeats an observation index.',
        )
    elif operation == 'choice':
        actual, available = (
            _row_counts(data.reshape((-1, *source.shape[1:]))),
            _row_counts(source),
        )
        positions = np.searchsorted(available[0], actual[0])
        valid = np.all(positions < available[0].size)
        if valid:
            valid = np.array_equal(available[0][positions], actual[0]) and np.all(
                actual[1] <= available[1][positions]
            )
        _require(
            valid,
            operation,
            'Without-replacement selection repeats source observations beyond availability.',
        )


def _check_allocation(operation: str, p: dict, source: np.ndarray | None, data: np.ndarray) -> None:
    _require(
        all(
            np.count_nonzero(data == label) == count
            for label, count in zip(p['labels'], p['counts'])
        ),
        operation,
        'Treatment allocation does not preserve the declared counts.',
    )


def _check_strata(operation: str, p: dict, source: np.ndarray | None, data: np.ndarray) -> None:
    groups = np.asarray(p['groups'])
    if operation == 'stratified_sample':
        offset = 0
        for label, count in zip(p['labels'], p['counts']):
            _require(
                np.all(groups[data[offset : offset + count]] == label),
                operation,
                'Selection changes its declared stratum membership or count.',
            )
            offset += count
    else:
        offset = 0
        for column in range(len(p['counts'][0])):
            length = sum(row[column] for row in p['counts'])
            selected = groups[data[offset : offset + length]]
            _require(
                all(
                    np.count_nonzero(selected == label) == counts[column]
                    for label, counts in zip(p['labels'], p['counts'])
                ),
                operation,
                'Partition changes its declared stratum counts.',
            )
            offset += length


def _check_bootstrap(operation: str, p: dict, source: np.ndarray | None, data: np.ndarray) -> None:
    if p['mode'] == 'block':
        positions = np.arange(1, p['sample_size'])
        within = positions % p['block_length'] != 0
        _require(
            np.all(data[:, 1:][:, within] == (data[:, :-1][:, within] + 1) % p['n']),
            operation,
            'Circular bootstrap blocks lost their observation order.',
        )
    elif p['mode'] == 'cluster':
        from ._operations import _cluster_rows

        rows = _cluster_rows(p['groups'])
        length = len(rows[0])
        cluster = np.empty(p['n'], dtype=np.int64)
        position = np.empty(p['n'], dtype=np.int64)
        for index, row in enumerate(rows):
            cluster[row] = index
            position[row] = np.arange(length)
        blocks = data.reshape(p['resamples'], -1, length)
        identities = cluster[blocks]
        _require(
            np.all(identities == identities[..., :1])
            and np.all(position[blocks] == np.arange(length)),
            operation,
            'Cluster bootstrap changed complete within-cluster observations.',
        )


def _check_latin_design(
    operation: str, p: dict, source: np.ndarray | None, data: np.ndarray
) -> None:
    bins = np.floor(data * p['n']).astype(np.int64)
    target = np.arange(p['n'])
    _require(
        np.array_equal(np.sort(bins, axis=0), np.broadcast_to(target[:, None], bins.shape)),
        operation,
        'The design lost its one-point-per-axis-stratum property.',
    )
    if operation == 'sudoku':
        codes = np.zeros(p['n'], dtype=np.int64)
        cells = 1
        for axis in range(p['d']):
            codes += np.floor(data[:, axis] * p['boxes']).astype(np.int64) * cells
            cells *= p['boxes']
        unique, counts = np.unique(codes, return_counts=True)
        _require(
            unique.size == cells and np.all(counts == p['n'] // cells),
            operation,
            'Sudoku coarse cells lost their declared balance.',
        )


def _check_separation(operation: str, p: dict, source: np.ndarray | None, data: np.ndarray) -> None:
    for index in range(p['n'] - 1):
        delta = data[index + 1 :] - data[index]
        _require(
            np.all(np.einsum('ij,ij->i', delta, delta) >= p['radius'] ** 2),
            operation,
            'Poisson disk points violate their minimum separation.',
        )


def _check_antithetic(operation: str, p: dict, source: np.ndarray | None, data: np.ndarray) -> None:
    half = p['n'] // 2
    center = p['loc'] if p['distribution'] == 'normal' else p['low'] / 2 + p['high'] / 2
    # Avoid overflowing pair sums for large finite locations.
    scale = max(abs(center), p.get('scale', 0), abs(p.get('low', 0)), abs(p.get('high', 0)), 1.0)
    deviations = (data[:half] / scale - center / scale) + (data[half:] / scale - center / scale)
    _require(
        np.allclose(deviations, 0, rtol=0, atol=8 * np.finfo(np.float64).eps),
        operation,
        'Antithetic output lost its declared reflection pairing.',
    )


_STRUCTURAL_CHECKS = {
    'balanced_allocation': _check_allocation,
    'stratified_sample': _check_strata,
    'stratified_split': _check_strata,
    'bootstrap': _check_bootstrap,
    'sobol': _check_latin_design,
    'latin_hypercube': _check_latin_design,
    'korobov': _check_latin_design,
    'sudoku': _check_latin_design,
    'poisson_disk': _check_separation,
    'antithetic': _check_antithetic,
}


def _row_counts(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    contiguous = np.ascontiguousarray(data)
    width = math.prod(data.shape[1:]) * data.dtype.itemsize
    if width == 0:
        return np.array([b''], dtype='S1'), np.array([data.shape[0]], dtype=np.int64)
    rows = contiguous.reshape(-1).view(np.dtype((np.void, width)))
    return np.unique(rows, return_counts=True)


def _member_mask(support: dict, data: np.ndarray) -> np.ndarray:
    kind = support['kind']
    if kind == 'union':
        result = np.zeros(data.shape, dtype=bool)
        for component in support['components']:
            result |= _member_mask(component, data)
        return result
    if kind == 'finite_values':
        return np.isin(data, support['values'])
    result = np.ones(data.shape, dtype=bool)
    if support.get('integral') and data.dtype.kind == 'f':
        result &= data == np.floor(data)
    low, high = support.get('low'), support.get('high')
    if low is not None:
        result &= data >= low if support.get('lower_inclusive', True) else data > low
    if high is not None:
        result &= data <= high if support.get('upper_inclusive', True) else data < high
    return result


def _in_support(support: dict, data: np.ndarray, source: np.ndarray | None) -> bool:
    kind = support['kind']
    if kind == 'interval' and data.dtype.kind in 'iu':
        low, high = support.get('low'), support.get('high')
        minimum, maximum = int(np.min(data)), int(np.max(data))
        return (
            low is None
            or (minimum >= low if support.get('lower_inclusive', True) else minimum > low)
        ) and (
            high is None
            or (maximum <= high if support.get('upper_inclusive', True) else maximum < high)
        )
    if kind in ('interval', 'union', 'finite_values'):
        return bool(_member_mask(support, data).all())
    if kind == 'integer_simplex':
        return _integer_simplex(support, data)
    if kind == 'simplex':
        return bool(
            np.all(data >= support['low'])
            and np.all(data <= support['high'])
            and np.allclose(data.sum(axis=-1), support['sum'], rtol=0, atol=support['tolerance'])
        )
    if kind == 'positive_definite_matrix':
        return bool(
            np.allclose(data, data.swapaxes(-1, -2), rtol=0, atol=1e-12)
            and np.all(np.linalg.eigvalsh(data) > 0)
        )
    if kind == 'source_rows':
        if source is None:
            return False
        available = _row_counts(source)
        selected = _row_counts(data.reshape((-1, *source.shape[1:])))
        return bool(np.isin(selected[0], available[0], assume_unique=True).all())
    return kind == 'finite_real_vector'


def _integer_simplex(support: dict, data: np.ndarray) -> bool:
    if not (np.all(data >= support['low']) and np.all(data <= support['high'])):
        return False
    remaining = np.full(data.shape[:-1], support['sum'], dtype=np.int64)
    for column in range(data.shape[-1]):
        if np.any(data[..., column] > remaining):
            return False
        remaining -= data[..., column]
    return bool(np.all(remaining == 0))
