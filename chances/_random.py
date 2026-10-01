"""Owned, named streams with versioned seed derivation; never global RNGs."""

from __future__ import annotations

import hashlib
import json
import unicodedata

import numpy as np

from ._errors import ChancesError

DERIVATION = 'sha256-seed-stream-v1'
ENGINES = {
    'pcg64dxsm': np.random.PCG64DXSM,
    'pcg64': np.random.PCG64,
    'philox': np.random.Philox,
    'sfc64': np.random.SFC64,
    'mt19937': np.random.MT19937,
}


def resolve_randomness(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) - {'seed', 'stream', 'engine'}:
        raise ChancesError('INVALID_RANDOMNESS', 'Use seed, stream, and engine fields only.')
    seed = value.get('seed')
    if type(seed) is not int or not 0 <= seed < 2**256:
        raise ChancesError(
            'SEED_REQUIRED', 'Declare an integer seed in [0, 2**256); booleans are not seeds.'
        )
    stream = value.get('stream', 'default')
    if not isinstance(stream, str) or not stream.strip():
        raise ChancesError(
            'INVALID_STREAM', 'Declare a nonempty stream name of at most 512 UTF-8 bytes.'
        )
    stream = unicodedata.normalize('NFC', stream)
    try:
        stream_bytes = stream.encode('utf-8')
    except UnicodeError as error:
        raise ChancesError('INVALID_STREAM', 'Stream names must be valid UTF-8.') from error
    if len(stream_bytes) > 512:
        raise ChancesError('INVALID_STREAM', 'The normalized stream name exceeds 512 UTF-8 bytes.')
    engine = value.get('engine', 'pcg64dxsm')
    if not isinstance(engine, str) or engine not in ENGINES:
        raise ChancesError(
            'UNKNOWN_ENGINE', 'Choose a catalogued bit generator.', {'engines': list(ENGINES)}
        )
    return {'seed': seed, 'stream': stream, 'engine': engine}


def generator(randomness: dict) -> np.random.Generator:
    payload = json.dumps(
        [randomness['seed'], randomness['stream']], ensure_ascii=False, separators=(',', ':')
    ).encode('utf-8')
    digest = hashlib.sha256(b'chances-stream-v1\x00' + payload).digest()
    words = [int.from_bytes(digest[i : i + 4], 'little') for i in range(0, 32, 4)]
    return np.random.Generator(ENGINES[randomness['engine']](np.random.SeedSequence(words)))


def _native(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: _native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_native(item) for item in value]
    return value


def state(rng: np.random.Generator) -> dict:
    snapshot = _native(rng.bit_generator.state)
    # SciPy QMC spawns a child stream without advancing the parent raw state.
    snapshot['seed_sequence'] = _native(rng.bit_generator.seed_seq.state)
    return snapshot


def _same_schema(actual: object, template: object) -> bool:
    if isinstance(template, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(template)
            and all(_same_schema(actual[k], template[k]) for k in template)
        )
    if isinstance(template, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(template)
            and all(_same_schema(a, b) for a, b in zip(actual, template))
        )
    if type(template) is int:
        return type(actual) is int and 0 <= actual < 2**256
    return type(actual) is type(template) and actual == template


def validate_state(snapshot: dict, randomness: dict, *, initial: bool = False) -> None:
    """Require complete engine and seed provenance without consuming raw draws."""
    rng = generator(randomness)
    expected = state(rng)
    if not _same_schema(snapshot, expected):
        raise ChancesError(
            'INVALID_RECEIPT',
            'RNG states must contain their complete native engine and SeedSequence schemas.',
        )
    seed_state = snapshot['seed_sequence']
    seed_expected = expected['seed_sequence']
    if (
        any(
            seed_state[key] != seed_expected[key]
            for key in seed_expected
            if key != 'n_children_spawned'
        )
        or seed_state['n_children_spawned'] >= 2**32
    ):
        raise ChancesError(
            'INVALID_RECEIPT', 'SeedSequence provenance differs from the declared seed and stream.'
        )
    if initial and snapshot != expected:
        raise ChancesError(
            'INVALID_RECEIPT', 'The initial RNG state does not match the declared seed and stream.'
        )
    if not initial:
        try:
            rng.bit_generator.state = {
                key: value for key, value in snapshot.items() if key != 'seed_sequence'
            }
            normalized = state(rng)
        except (TypeError, ValueError, KeyError, OverflowError) as error:
            raise ChancesError(
                'INVALID_RECEIPT', 'The recorded state is not valid for the declared bit generator.'
            ) from error
        if any(normalized[key] != snapshot[key] for key in normalized if key != 'seed_sequence'):
            raise ChancesError(
                'INVALID_RECEIPT', 'The engine state contains lossy or out-of-range values.'
            )
        _validate_engine_bounds(snapshot, randomness)


def _validate_engine_bounds(snapshot: dict, randomness: dict) -> None:
    if randomness['engine'] == 'mt19937' and snapshot['state']['pos'] > 624:
        raise ChancesError('INVALID_RECEIPT', 'Mersenne Twister state position exceeds its buffer.')
    if randomness['engine'] == 'philox' and snapshot['buffer_pos'] > 4:
        raise ChancesError('INVALID_RECEIPT', 'Philox state position exceeds its buffer.')
    if 'has_uint32' in snapshot and snapshot['has_uint32'] not in (0, 1):
        raise ChancesError('INVALID_RECEIPT', "The engine's cached integer flag is invalid.")
