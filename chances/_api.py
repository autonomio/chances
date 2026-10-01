"""Validated protocols, scientific arrays, and independently verifiable bundles."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import numpy as np
import scipy

from . import __version__
from ._errors import ChancesError
from ._publication import publish_directory
from ._random import DERIVATION, generator, resolve_randomness, state, validate_state

SPEC_VERSION = 1
RECEIPT_VERSION = 1
MAX_JSON_BYTES = 1_048_576
DEFAULT_LIMITS = {'max_values': 10_000_000, 'max_bytes': 268_435_456, 'max_work': 100_000_000}
_ARRAY_KINDS = frozenset('biufUS')
_NATIVE_SCALARS = tuple(cast(dict[object, object], np.sctypeDict).values())
_PATH_TYPES = (str, type(Path()))


def _literal_json(value: object) -> None:
    if type(value) is dict:
        for key, item in cast(dict[object, object], value).items():
            if not any(type(key) is native for native in (str, int, float, bool, type(None))):
                raise ChancesError('INVALID_JSON', 'JSON keys must be native literal values.')
            _literal_json(item)
    elif type(value) is list or type(value) is tuple:
        for item in cast(list[object] | tuple[object, ...], value):
            _literal_json(item)
    elif not any(type(value) is native for native in (str, int, float, bool, type(None))):
        raise ChancesError(
            'INVALID_JSON', 'Use native JSON values; subclasses and callbacks are forbidden.'
        )


def _json(value: object) -> str:
    try:
        _literal_json(value)
        encoded = json.dumps(
            value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')
        )
        encoded.encode('utf-8')
        return encoded
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError) as error:
        raise ChancesError('INVALID_JSON', 'Use finite, UTF-8 JSON values only.') from error


def _json_equal(left: object, right: object) -> bool:
    return _json(left) == _json(right)


def _artifact_path(directory: str | Path, *, role: str) -> Path:
    code = 'OUTPUT_FAILED' if role == 'output' else 'INVALID_BUNDLE'
    if not any(type(directory) is native for native in _PATH_TYPES):
        raise ChancesError(
            code, 'Use a native string or pathlib path; path callbacks are forbidden.'
        )
    if '\x00' in str(directory):
        raise ChancesError(code, 'Native artifact paths cannot contain NUL bytes.')
    return Path(directory).expanduser().absolute()


def _output_destination(directory: str | Path) -> Path:
    destination = _artifact_path(directory, role='output')
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as error:
        raise ChancesError(
            'OUTPUT_FAILED',
            'The destination parent cannot be prepared.',
            {'path': str(destination), 'error': str(error)},
        ) from error
    return destination


def _json_hash(value: object) -> str:
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _read_json(path: Path) -> object:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ChancesError(
                    'INVALID_JSON', 'JSON field names must be unique.', {'field': key}
                )
            result[key] = value
        return result

    try:
        if path.is_symlink() or not path.is_file():
            raise ChancesError(
                'INVALID_JSON',
                'Use a regular local JSON file; special files and symbolic links are unsupported.',
            )
        with path.open('rb') as handle:
            raw = handle.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            raise ChancesError(
                'RESOURCE_LIMIT', 'JSON documents must fit the one MiB protocol limit.'
            )
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
        _json(value)
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, ChancesError):
            raise
        raise ChancesError(
            'INVALID_JSON', 'Use an existing, finite UTF-8 JSON document.', {'path': str(path)}
        ) from error


def _limits(value: object) -> dict:
    if not isinstance(value, dict) or set(value) - set(DEFAULT_LIMITS):
        raise ChancesError('INVALID_LIMITS', 'Use max_values, max_bytes, and max_work only.')
    resolved = {**DEFAULT_LIMITS, **value}
    if any(type(item) is not int or not 1 <= item <= 2**63 - 1 for item in resolved.values()):
        raise ChancesError(
            'INVALID_LIMITS', 'Resource limits must be positive integers below 2**63.'
        )
    return resolved


def _array_hash(data: np.ndarray) -> str:
    """Bind dtype, shape and C-order bytes; independent of strides and NPY headers."""
    canonical = np.ascontiguousarray(data)
    digest = hashlib.sha256(b'chances-array-v1\x00')
    digest.update(_json({'dtype': data.dtype.str, 'shape': list(data.shape)}).encode('utf-8'))
    digest.update(b'\x00')
    # Bounded copies: NumPy memoryviews for Unicode do not support cast on all builds.
    byte_view = canonical.reshape(-1).view(np.uint8)
    for offset in range(0, byte_view.size, 1_048_576):
        digest.update(memoryview(byte_view[offset : offset + 1_048_576]))
    return digest.hexdigest()


def _array_info(data: np.ndarray) -> dict[str, object]:
    return {
        'dtype': data.dtype.str,
        'shape': list(data.shape),
        'values': int(data.size),
        'bytes': int(data.nbytes),
        'sha256': _array_hash(data),
    }


def _validate_array(data: np.ndarray, limits: dict, *, role: str) -> None:
    if data.dtype.kind not in _ARRAY_KINDS or data.dtype.hasobject or data.ndim > 16:
        raise ChancesError(
            'UNSUPPORTED_DTYPE',
            'Use native numeric, Boolean, or fixed-width string arrays of at most 16 dimensions.',
            {'role': role, 'dtype': str(data.dtype)},
        )
    if data.size > limits['max_values'] or data.nbytes > limits['max_bytes']:
        raise ChancesError(
            'RESOURCE_LIMIT',
            'The array exceeds the declared value or byte limit.',
            {'role': role, 'values': int(data.size), 'bytes': int(data.nbytes), 'limits': limits},
        )
    if data.dtype.kind == 'f':
        # Bound temporary validation buffers, including for memory-mapped input.
        flat = data.reshape(-1)
        for offset in range(0, flat.size, 1_048_576):
            if not np.isfinite(flat[offset : offset + 1_048_576]).all():
                raise ChancesError(
                    'NONFINITE_RESULT' if role == 'output' else 'INVALID_SOURCE',
                    'Scientific arrays must contain finite values.',
                    {'role': role},
                )


def _load_npy(path: Path, limits: dict, *, role: str) -> np.ndarray:
    try:
        if path.suffix != '.npy' or path.is_symlink() or not path.is_file():
            raise ChancesError(
                'INVALID_SOURCE',
                'Use a regular .npy file; pickle and symbolic links are unsupported.',
            )
        if path.stat().st_size > limits['max_bytes'] + 65_536:
            raise ChancesError(
                'RESOURCE_LIMIT', 'The NPY artifact exceeds the declared byte limit.'
            )
        data = np.load(path, allow_pickle=False, mmap_mode='r', max_header_size=16_384)
        if not isinstance(data, np.ndarray):
            raise ChancesError('INVALID_SOURCE', 'Use a single native NumPy array.')
        _validate_array(data, limits, role=role)
        return data
    except (OSError, ValueError, TypeError, EOFError, OverflowError) as error:
        if isinstance(error, ChancesError):
            raise
        raise ChancesError(
            'INVALID_SOURCE', 'The array cannot be loaded without pickle.', {'path': str(path)}
        ) from error


def _collect_leaves(item: object, leaves: list, limits: dict, depth: int = 0) -> None:
    if depth > 16:
        raise ChancesError('INVALID_SOURCE', 'Source sequences support at most 16 dimensions.')
    if type(item) is list or type(item) is tuple:
        for child in item:
            _collect_leaves(child, leaves, limits, depth + 1)
    else:
        if any(type(item) is scalar for scalar in _NATIVE_SCALARS):
            item = item.item()
        if not any(type(item) is native for native in (bool, int, float, str, bytes)):
            raise ChancesError(
                'INVALID_SOURCE',
                'Source sequences must contain native literal values; callbacks and custom objects are forbidden.',
            )
        leaves.append(item)
        if len(leaves) > limits['max_values']:
            raise ChancesError(
                'RESOURCE_LIMIT', 'The source sequence exceeds the declared value limit.'
            )


def _sequence_array(value: list | tuple, limits: dict) -> np.ndarray:
    leaves = []
    _collect_leaves(value, leaves, limits)
    kinds = {'numeric' if type(item) in (int, float) else type(item).__name__ for item in leaves}
    if len(kinds) > 1:
        raise ChancesError(
            'INVALID_SOURCE',
            'Source fields must have consistent native types; mixed identifiers and numbers require an explicitly typed array.',
        )
    width = max((len(item) for item in leaves), default=0) if kinds <= {'str', 'bytes'} else 8
    estimate = len(leaves) * max(1, width) * (4 if kinds == {'str'} else 1)
    if estimate > limits['max_bytes']:
        raise ChancesError(
            'RESOURCE_LIMIT',
            'The source sequence exceeds the declared byte limit before conversion.',
        )
    try:
        data = np.asarray(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ChancesError('INVALID_SOURCE', 'Use a rectangular native array.') from error
    if data.dtype.kind == 'f' and any(
        type(item) is int and (not math.isfinite(float(item)) or int(float(item)) != item)
        for item in leaves
    ):
        raise ChancesError(
            'LOSSY_SOURCE',
            'A source integer cannot be represented exactly in the inferred floating dtype; declare a lossless array.',
        )
    return data


def _source(value: object, limits: dict) -> np.ndarray | None:
    if value is None:
        return None
    path = None
    before = None
    if any(type(value) is native for native in _PATH_TYPES):
        path = Path(value).expanduser().absolute()
        data = _load_npy(path, limits, role='source')
        before = _file_hash(path)
    elif type(value) is np.ndarray or type(value) is np.memmap:
        data = value
    elif issubclass(type(value), np.ndarray):
        raise ChancesError(
            'INVALID_SOURCE',
            'Resolve missingness and convert subclasses to an explicit native array; masked arrays and array callbacks are unsupported.',
        )
    elif type(value) is list or type(value) is tuple:
        data = _sequence_array(value, limits)
    else:
        raise ChancesError(
            'INVALID_SOURCE', 'Use a NumPy array, rectangular sequence, or local .npy path.'
        )
    _validate_array(data, limits, role='source')
    data = np.array(data, copy=True, order='C')
    if path is not None and _file_hash(path) != before:
        raise ChancesError(
            'SOURCE_CHANGED', 'The source changed during snapshotting; use a stable input.'
        )
    data.flags.writeable = False
    return data


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1_048_576), b''):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as error:
        raise ChancesError(
            'INVALID_SOURCE', 'The source file is unavailable.', {'path': str(path)}
        ) from error


def _environment() -> dict[str, object]:
    return {
        'python': platform.python_version(),
        'python_implementation': platform.python_implementation(),
        'python_build': list(platform.python_build()),
        'platform': platform.platform(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'byteorder': sys.byteorder,
        'cpu_count': os.cpu_count(),
        'numpy_build': np.show_config(mode='dicts'),
        'scipy_build': scipy.show_config(mode='dicts'),
        'thread_environment': {
            key: os.environ.get(key)
            for key in (
                'OMP_NUM_THREADS',
                'OPENBLAS_NUM_THREADS',
                'MKL_NUM_THREADS',
                'VECLIB_MAXIMUM_THREADS',
                'BLIS_NUM_THREADS',
            )
        },
    }


def _resolve(spec: object, source: object) -> tuple[dict, np.ndarray | None]:
    from ._operations import resolve_operation

    if any(type(spec) is native for native in _PATH_TYPES):
        spec = _read_json(Path(spec).expanduser())
    if not issubclass(type(spec), dict):
        raise ChancesError(
            'INVALID_SPEC', 'Declare a JSON object or local JSON specification path.'
        )
    encoded = _json(spec).encode('utf-8')
    if len(encoded) > MAX_JSON_BYTES:
        raise ChancesError('RESOURCE_LIMIT', 'Specifications must fit the one MiB protocol limit.')
    spec = json.loads(encoded)
    unknown = set(spec) - {'version', 'operation', 'parameters', 'randomness', 'limits'}
    if unknown or type(spec.get('version', 1)) is not int or spec.get('version', 1) != SPEC_VERSION:
        raise ChancesError(
            'INVALID_SPEC',
            'Use specification version 1 and documented fields.',
            {'unknown_fields': sorted(unknown)},
        )
    operation = spec.get('operation')
    if not isinstance(operation, str) or not operation:
        raise ChancesError('UNKNOWN_OPERATION', 'Declare an operation from the catalog.')
    parameters = spec.get('parameters', {})
    if not isinstance(parameters, dict):
        raise ChancesError('INVALID_PARAMETERS', 'Operation parameters must be a JSON object.')
    limits = _limits(spec.get('limits', {}))
    snapshot = _source(source, limits)
    randomness = resolve_randomness(spec.get('randomness', {}))
    try:
        parameters = resolve_operation(operation, parameters, snapshot, limits)
    except (TypeError, ValueError, OverflowError) as error:
        if isinstance(error, ChancesError):
            raise
        raise ChancesError(
            'INVALID_PARAMETERS',
            'The declared parameters do not satisfy the operation.',
            {'operation': operation, 'error': str(error)},
        ) from error
    resolved = {
        'version': SPEC_VERSION,
        'operation': operation,
        'parameters': parameters,
        'randomness': randomness,
        'limits': limits,
    }
    from ._checks import preflight_checks

    preflight_checks(operation, parameters, snapshot, limits)
    _json(resolved)
    return resolved, snapshot


def inspect(spec: object, *, source: object = None) -> dict:
    """Resolve defaults, validate domains and resource limits without drawing values."""
    from ._operations import catalog, operation_output, operation_postconditions

    resolved, snapshot = _resolve(spec, source)
    entries = catalog()
    # Registry catalogs may place operation entries under the operations key.
    operations = entries.get('operations', entries)
    shape, dtype = operation_output(resolved['operation'], resolved['parameters'], snapshot)
    values = math.prod(shape)
    return {
        'resolved_spec': resolved,
        'source': _array_info(snapshot) if snapshot is not None else None,
        'operation': operations.get(resolved['operation']),
        'output': {
            'dtype': dtype.str,
            'shape': list(shape),
            'values': values,
            'bytes': values * dtype.itemsize,
        },
        'postconditions': operation_postconditions(
            resolved['operation'], resolved['parameters'], snapshot
        ),
        'replay': 'Identical source, resolved specification, implementation, and recorded environment.',
    }


@dataclass(frozen=True)
class Generated:
    """A checked array and JSON receipt; publication rejects post-generation changes."""

    data: np.ndarray
    receipt: dict
    _source_data: np.ndarray | None = field(default=None, repr=False)
    _data_digest: str = field(init=False, repr=False)
    _receipt_digest: str = field(init=False, repr=False)
    _source_digest: str | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.data.flags.writeable = False
        if self._source_data is not None:
            self._source_data.flags.writeable = False
        object.__setattr__(self, '_data_digest', _array_hash(self.data))
        object.__setattr__(self, '_receipt_digest', _json_hash(self.receipt))
        object.__setattr__(
            self,
            '_source_digest',
            _array_hash(self._source_data) if self._source_data is not None else None,
        )

    def write(self, directory: str | Path) -> Path:
        """Stage NPY/JSON artifacts together, then publish a new local directory."""
        data = np.array(self.data, copy=True, order='C')
        receipt = json.loads(_json(self.receipt))
        source = (
            np.array(self._source_data, copy=True, order='C')
            if self._source_data is not None
            else None
        )
        if (
            _array_hash(data) != self._data_digest
            or _json_hash(receipt) != self._receipt_digest
            or (_array_hash(source) if source is not None else None) != self._source_digest
        ):
            raise ChancesError(
                'RESULT_CHANGED',
                'Data, source, or receipt changed; generate again before publishing.',
            )
        destination = _output_destination(directory)
        temporary = None
        try:
            if os.path.lexists(destination):
                raise ChancesError(
                    'OUTPUT_EXISTS',
                    'Choose a new directory; existing artifacts are never overwritten.',
                )
            temporary = Path(tempfile.mkdtemp(prefix='.chances-', dir=destination.parent))
            with (temporary / 'data.npy').open('wb') as handle:
                np.save(handle, data, allow_pickle=False)
            if source is not None:
                with (temporary / 'source.npy').open('wb') as handle:
                    np.save(handle, source, allow_pickle=False)
            (temporary / 'recipe.json').write_text(_json(receipt['spec']) + '\n', encoding='utf-8')
            (temporary / 'receipt.json').write_text(_json(receipt) + '\n', encoding='utf-8')
            # Validate the actual staged bytes before making the directory visible.
            verify(temporary)
            if os.path.lexists(destination):
                raise ChancesError('OUTPUT_EXISTS', 'The destination appeared during publication.')
            publish_directory(temporary, destination)
            temporary = None
            return destination
        except FileExistsError as error:
            raise ChancesError(
                'OUTPUT_EXISTS', 'The destination appeared during publication.'
            ) from error
        except OSError as error:
            raise ChancesError(
                'OUTPUT_FAILED',
                'Artifact publication failed.',
                {'path': str(destination), 'error': str(error)},
            ) from error
        finally:
            if temporary is not None:
                shutil.rmtree(temporary)


def generate(spec: object, *, source: object = None, output: str | Path | None = None) -> Generated:
    """Execute one declared scientific operation using an isolated named stream."""
    from ._operations import execute_operation, operation_postconditions

    resolved, snapshot = _resolve(spec, source)
    rng = generator(resolved['randomness'])
    before = state(rng)
    try:
        data = np.asarray(
            execute_operation(resolved['operation'], resolved['parameters'], rng, snapshot)
        )
    except (ValueError, TypeError, OverflowError, np.linalg.LinAlgError) as error:
        if isinstance(error, ChancesError):
            raise
        raise ChancesError(
            'OPERATION_FAILED',
            'The operation could not satisfy the declared protocol.',
            {'operation': resolved['operation'], 'error': str(error)},
        ) from error
    _validate_array(data, resolved['limits'], role='output')
    from ._checks import check_output

    check_output(resolved['operation'], resolved['parameters'], snapshot, data)
    data = np.ascontiguousarray(data) if data.ndim else np.array(data, copy=True)
    output_info = _array_info(data)
    receipt = {
        'receipt_version': RECEIPT_VERSION,
        'versions': {'chances': __version__, 'numpy': np.__version__, 'scipy': scipy.__version__},
        'environment': _environment(),
        'spec': resolved,
        'spec_sha256': _json_hash(resolved),
        'contract': operation_postconditions(
            resolved['operation'], resolved['parameters'], snapshot
        ),
        'source': _array_info(snapshot) if snapshot is not None else None,
        'randomness': {
            **resolved['randomness'],
            'derivation': DERIVATION,
            'state_before': before,
            'state_after': state(rng),
        },
        'checks': {
            'finite': True,
            'supported_dtype': True,
            'resource_limits': True,
            'shape': True,
            'dtype': True,
            'declared_support': True,
            'structural_constraints': True,
        },
        'output': output_info,
    }
    receipt['receipt_sha256'] = _json_hash(receipt)
    if len(_json(receipt).encode('utf-8')) > MAX_JSON_BYTES:
        raise ChancesError('RESOURCE_LIMIT', 'The receipt exceeds the one MiB protocol limit.')
    result = Generated(data, receipt, snapshot)
    if output is not None:
        result.write(output)
    return result


def _check_array_info(data: np.ndarray, info: object, *, role: str) -> None:
    if not isinstance(info, dict) or not _json_equal(info, _array_info(data)):
        raise ChancesError(
            'INTEGRITY_MISMATCH',
            'The artifact differs from its recorded content hash, dtype, or shape.',
            {'role': role},
        )


def _bundle_files(path: Path) -> set[str]:
    actual_files = {entry.name for entry in path.iterdir()}
    required = {'data.npy', 'recipe.json', 'receipt.json'}
    if not required.issubset(actual_files) or actual_files - required - {'source.npy'}:
        raise ChancesError(
            'INVALID_BUNDLE', 'The bundle must contain its NPY and JSON artifacts only.'
        )
    for filename in actual_files:
        if (path / filename).is_symlink() or not (path / filename).is_file():
            raise ChancesError('INVALID_BUNDLE', 'Bundle artifacts must be regular files.')
    return actual_files


def _receipt_schema(receipt: object, recipe: object) -> None:
    receipt_keys = {
        'receipt_version',
        'versions',
        'environment',
        'spec',
        'spec_sha256',
        'source',
        'randomness',
        'checks',
        'contract',
        'output',
        'receipt_sha256',
    }
    if (
        not isinstance(receipt, dict)
        or set(receipt) != receipt_keys
        or type(receipt.get('receipt_version')) is not int
        or receipt['receipt_version'] != RECEIPT_VERSION
    ):
        raise ChancesError(
            'INVALID_RECEIPT', 'Use a supported receipt schema with every required field.'
        )
    digest = receipt['receipt_sha256']
    contents = {key: value for key, value in receipt.items() if key != 'receipt_sha256'}
    if not isinstance(digest, str) or digest != _json_hash(contents):
        raise ChancesError('INTEGRITY_MISMATCH', 'The receipt changed after generation.')
    if not _json_equal(recipe, receipt['spec']) or _json_hash(recipe) != receipt['spec_sha256']:
        raise ChancesError('INTEGRITY_MISMATCH', 'The stored recipe differs from the receipt.')
    if not isinstance(recipe, dict):
        raise ChancesError('INVALID_RECEIPT', 'The receipt must contain a specification object.')


def _bundle_arrays(
    path: Path, actual_files: set[str], receipt: dict, recipe: dict
) -> tuple[np.ndarray, np.ndarray | None]:
    limits = _limits(recipe.get('limits', {}))
    source_present = receipt['source'] is not None
    if source_present != ('source.npy' in actual_files):
        raise ChancesError(
            'INVALID_BUNDLE', "The source snapshot must match the receipt's source declaration."
        )
    source = (
        np.array(_load_npy(path / 'source.npy', limits, role='source'), copy=True, order='C')
        if source_present
        else None
    )
    data = np.array(_load_npy(path / 'data.npy', limits, role='output'), copy=True, order='C')
    if source is not None:
        _check_array_info(source, receipt['source'], role='source')
    _check_array_info(data, receipt['output'], role='output')
    return data, source


def _receipt_contract(
    receipt: dict, recipe: dict, source: np.ndarray | None, data: np.ndarray
) -> None:
    if not _json_equal(
        receipt['checks'],
        {
            'finite': True,
            'supported_dtype': True,
            'resource_limits': True,
            'shape': True,
            'dtype': True,
            'declared_support': True,
            'structural_constraints': True,
        },
    ):
        raise ChancesError('INVALID_RECEIPT', 'The receipt does not declare the required checks.')
    # Validate the saved contract under this reader without drawing RNG values.
    resolved, _ = _resolve(recipe, source)
    from ._checks import check_output
    from ._operations import operation_postconditions

    if not _json_equal(
        receipt['contract'],
        operation_postconditions(resolved['operation'], resolved['parameters'], source),
    ):
        raise ChancesError(
            'INVALID_RECEIPT', 'The recorded output contract differs from the declared protocol.'
        )
    check_output(resolved['operation'], resolved['parameters'], source, data)
    if not _json_equal(resolved, recipe):
        raise ChancesError(
            'INVALID_RECEIPT', 'Saved specifications must include their resolved defaults.'
        )


def _receipt_randomness(receipt: dict, recipe: dict) -> None:
    randomness = receipt['randomness']
    if not isinstance(randomness, dict) or set(randomness) != {
        'seed',
        'stream',
        'engine',
        'derivation',
        'state_before',
        'state_after',
    }:
        raise ChancesError('INVALID_RECEIPT', 'The RNG provenance is incomplete.')
    if (
        any(
            not _json_equal(randomness.get(key), recipe['randomness'][key])
            for key in ('seed', 'stream', 'engine')
        )
        or randomness['derivation'] != DERIVATION
        or not isinstance(randomness['state_before'], dict)
        or not isinstance(randomness['state_after'], dict)
    ):
        raise ChancesError('INVALID_RECEIPT', 'RNG provenance must agree with the declared stream.')
    validate_state(randomness['state_before'], recipe['randomness'], initial=True)
    validate_state(randomness['state_after'], recipe['randomness'])


def _receipt_environment(receipt: dict) -> None:
    versions = receipt['versions']
    environment = receipt['environment']
    environment_keys = {
        'python',
        'python_implementation',
        'python_build',
        'platform',
        'machine',
        'processor',
        'byteorder',
        'cpu_count',
        'numpy_build',
        'scipy_build',
        'thread_environment',
    }
    if (
        not isinstance(versions, dict)
        or set(versions) != {'chances', 'numpy', 'scipy'}
        or any(not isinstance(v, str) or not v for v in versions.values())
        or not isinstance(environment, dict)
        or set(environment) != environment_keys
    ):
        raise ChancesError(
            'INVALID_RECEIPT', 'Complete implementation versions and environment must be declared.'
        )


def verify(directory: str | Path) -> Generated:
    """Check stored protocol, receipt and array integrity; does not regenerate values."""
    path = _artifact_path(directory, role='bundle')
    if not path.is_dir() or path.is_symlink():
        raise ChancesError('INVALID_BUNDLE', 'Use a regular Chances bundle directory.')
    try:
        actual_files = _bundle_files(path)
        receipt = _read_json(path / 'receipt.json')
        recipe = _read_json(path / 'recipe.json')
        _receipt_schema(receipt, recipe)
        data, source = _bundle_arrays(path, actual_files, receipt, recipe)
        _receipt_contract(receipt, recipe, source, data)
        _receipt_randomness(receipt, recipe)
        _receipt_environment(receipt)
        return Generated(
            np.array(data, copy=True, order='C'),
            receipt,
            np.array(source, copy=True, order='C') if source is not None else None,
        )
    except (OSError, KeyError, TypeError) as error:
        raise ChancesError(
            'INVALID_BUNDLE', 'The artifact bundle is malformed.', {'error': str(error)}
        ) from error


def replay(directory: str | Path, *, output: str | Path | None = None) -> Generated:
    """Regenerate a verified bundle, rejecting incompatible environments or values."""
    saved = verify(directory)
    versions = {'chances': __version__, 'numpy': np.__version__, 'scipy': scipy.__version__}
    if saved.receipt['versions'] != versions or not _json_equal(
        saved.receipt['environment'], _environment()
    ):
        raise ChancesError(
            'REPLAY_INCOMPATIBLE',
            'Restore the recorded implementation and environment before exact regeneration.',
            {'recorded_versions': saved.receipt['versions'], 'current_versions': versions},
        )
    result = generate(saved.receipt['spec'], source=saved._source_data)
    if not _json_equal(result.receipt, saved.receipt) or _array_hash(result.data) != _array_hash(
        saved.data
    ):
        raise ChancesError(
            'REPLAY_MISMATCH', 'Regeneration did not reproduce the recorded values and evidence.'
        )
    if output is not None:
        result.write(output)
    return result
