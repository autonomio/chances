"""Scientific protocols must survive retries, artifact transfer, and corruption checks."""

import json
import random
import subprocess
import sys

import numpy as np
import pytest

import chances as ch
from chances._api import _array_hash, _json_hash
from chances._random import generator, resolve_randomness


def spec(operation='normal', parameters=None, **randomness):
    return {
        'version': 1,
        'operation': operation,
        'parameters': parameters if parameters is not None else {'size': 64, 'loc': 0, 'scale': 1},
        'randomness': {'seed': 42, 'stream': 'trial/replicate-1', **randomness},
    }


def test_protocol_retries_named_streams_and_receipts():
    before_python = random.getstate()
    before_numpy = np.random.get_state()
    first = ch.generate(spec())
    ch.generate(spec(stream='trial/replicate-2'))
    second = ch.generate(spec())
    np.testing.assert_array_equal(first.data, second.data)
    assert first.receipt == second.receipt
    assert first.receipt['randomness']['state_before'] != first.receipt['randomness']['state_after']
    assert random.getstate() == before_python
    assert all(np.array_equal(a, b) for a, b in zip(np.random.get_state(), before_numpy))
    assert not np.array_equal(first.data, ch.generate(spec(stream='trial/replicate-2')).data)


@pytest.mark.parametrize('engine', ['pcg64dxsm', 'pcg64', 'philox', 'sfc64', 'mt19937'])
def test_engine_identity_and_complete_replay(tmp_path, engine):
    result = ch.generate(spec(engine=engine), output=tmp_path / engine)
    assert result.receipt['randomness']['engine'] == engine
    restored = ch.verify(tmp_path / engine)
    replayed = ch.replay(tmp_path / engine, output=tmp_path / (engine + '-retry'))
    np.testing.assert_array_equal(result.data, restored.data)
    np.testing.assert_array_equal(result.data, replayed.data)
    assert result.receipt == replayed.receipt
    with pytest.raises(ch.ChancesError, match='never overwritten'):
        result.write(tmp_path / engine)


def test_source_snapshot_preserved_and_replayed(tmp_path):
    source = np.arange(60).reshape(20, 3)
    before = source.copy()
    recipe = spec('shuffle', {})
    result = ch.generate(recipe, source=source, output=tmp_path / 'rows')
    np.testing.assert_array_equal(source, before)
    source[:] = -1
    replayed = ch.replay(tmp_path / 'rows')
    np.testing.assert_array_equal(replayed.data, result.data)
    assert sorted(map(tuple, result.data)) == sorted(map(tuple, before))
    assert (tmp_path / 'rows' / 'source.npy').exists()


def test_source_hash_independent_of_strides(tmp_path):
    data = np.arange(16).reshape(4, 4)
    assert _array_hash(data) == _array_hash(np.asfortranarray(data))
    assert _array_hash(data) != _array_hash(data.reshape(8, 2))
    assert _array_hash(data) != _array_hash(data.astype(np.float64))


def test_inspect_draws_no_randomness(monkeypatch):
    monkeypatch.setattr(
        'chances._api.generator', lambda *args: pytest.fail('inspection created RNG')
    )
    result = ch.inspect(spec())
    assert result['resolved_spec']['randomness']['engine'] == 'pcg64dxsm'
    assert result['source'] is None


@pytest.mark.parametrize('change', ['data', 'receipt', 'recipe', 'source'])
def test_corrupted_bundle_is_rejected(tmp_path, change):
    bundle = tmp_path / change
    ch.generate(spec('shuffle', {}), source=np.arange(24).reshape(8, 3), output=bundle)
    if change in ('data', 'source'):
        np.save(bundle / (change + '.npy'), np.zeros((8, 3), dtype=np.int64))
    else:
        path = bundle / (change + '.json')
        value = json.loads(path.read_text())
        if change == 'receipt':
            value['output']['values'] = 999
        else:
            value['randomness']['seed'] += 1
        path.write_text(json.dumps(value))
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INTEGRITY_MISMATCH'


@pytest.mark.parametrize('change', ['data', 'receipt', 'source'])
def test_mutation_cannot_publish_stale_evidence(tmp_path, change):
    result = ch.generate(spec('shuffle', {}), source=np.arange(12).reshape(4, 3))
    if change == 'receipt':
        result.receipt['output']['values'] = 999
    else:
        data = result.data if change == 'data' else result._source_data
        data.flags.writeable = True
        data.flat[0] = -999
    with pytest.raises(ch.ChancesError) as error:
        result.write(tmp_path / change)
    assert error.value.code == 'RESULT_CHANGED'
    assert not (tmp_path / change).exists()


def test_recorded_environment_required_only_for_regeneration(tmp_path):
    bundle = tmp_path / 'old'
    ch.generate(spec(), output=bundle)
    path = bundle / 'receipt.json'
    value = json.loads(path.read_text())
    value['environment']['machine'] = 'different-architecture'
    value['receipt_sha256'] = _json_hash({k: v for k, v in value.items() if k != 'receipt_sha256'})
    path.write_text(json.dumps(value))
    ch.verify(bundle)
    with pytest.raises(ch.ChancesError) as error:
        ch.replay(bundle)
    assert error.value.code == 'REPLAY_INCOMPATIBLE'


@pytest.mark.parametrize(
    'change,code',
    [
        ({'randomness': {}}, 'SEED_REQUIRED'),
        ({'randomness': {'seed': True}}, 'SEED_REQUIRED'),
        ({'randomness': {'seed': -1}}, 'SEED_REQUIRED'),
        ({'randomness': {'seed': 1, 'engine': 'typo'}}, 'UNKNOWN_ENGINE'),
        ({'randomness': {'seed': 1, 'stream': ''}}, 'INVALID_STREAM'),
        ({'version': True}, 'INVALID_SPEC'),
        ({'version': 999}, 'INVALID_SPEC'),
        ({'arbitrary_code': "print('no')"}, 'INVALID_SPEC'),
        ({'limits': {'max_values': 0}}, 'INVALID_LIMITS'),
        ({'parameters': {'size': 11}, 'limits': {'max_values': 10}}, 'RESOURCE_LIMIT'),
    ],
)
def test_invalid_protocols_fail_before_execution(monkeypatch, change, code):
    recipe = {**spec(), **change}
    monkeypatch.setattr(
        'chances._api.generator', lambda *args: pytest.fail('invalid protocol reached RNG')
    )
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(recipe)
    assert error.value.code == code


def test_pickle_source_and_symlink_artifacts_rejected(tmp_path):
    source = tmp_path / 'objects.npy'
    np.save(source, np.array([{'payload': 'literal'}], dtype=object))
    with pytest.raises(ch.ChancesError):
        ch.generate(spec('shuffle', {}), source=source)
    bundle = tmp_path / 'bundle'
    ch.generate(spec(), output=bundle)
    original = tmp_path / 'original.npy'
    (bundle / 'data.npy').rename(original)
    (bundle / 'data.npy').symlink_to(original)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_BUNDLE'


def test_staging_failure_leaves_no_partial_output(tmp_path, monkeypatch):
    result = ch.generate(spec())

    def fail(*args, **kwargs):
        raise OSError('simulated full filesystem')

    monkeypatch.setattr(np, 'save', fail)
    with pytest.raises(ch.ChancesError) as error:
        result.write(tmp_path / 'failed')
    assert error.value.code == 'OUTPUT_FAILED'
    assert list(tmp_path.iterdir()) == []


def test_cli_uses_same_contract_and_structured_errors(tmp_path):
    path = tmp_path / 'recipe.json'
    path.write_text(json.dumps(spec()))
    run = subprocess.run(
        [sys.executable, '-m', 'chances', 'generate', str(path), '--output', str(tmp_path / 'cli')],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)['receipt'] == ch.verify(tmp_path / 'cli').receipt
    retry = subprocess.run(
        [sys.executable, '-m', 'chances', 'generate', str(path), '--output', str(tmp_path / 'cli')],
        capture_output=True,
        text=True,
    )
    assert retry.returncode == 2
    assert json.loads(retry.stderr)['error']['code'] == 'OUTPUT_EXISTS'


def test_canonical_named_stream_golden_vectors():
    # Raw bits isolate the pinned seed derivation from distribution transformations.
    rng = generator(
        resolve_randomness({'seed': 42, 'stream': 'trial/replicate-1', 'engine': 'philox'})
    )
    assert rng.bit_generator.random_raw(4).tolist() == [
        11920217634743232345,
        3139727636019262027,
        10980379360790395042,
        503661341492306314,
    ]


def test_unicode_stream_resolution_is_idempotent():
    composed = ch.generate(spec(stream='trial/café'))
    decomposed = ch.generate(spec(stream='trial/cafe\u0301'))
    assert composed.receipt == decomposed.receipt
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec(stream='\u0344' * 200))
    assert error.value.code == 'INVALID_STREAM'


def test_scalar_hash_differs_from_vector_hash():
    assert _array_hash(np.array(42)) != _array_hash(np.array([42]))


def test_qmc_receipt_records_child_stream_spawning(tmp_path):
    result = ch.generate(spec('sobol', {'n': 16, 'd': 3}), output=tmp_path / 'qmc')
    before = result.receipt['randomness']['state_before']['seed_sequence']
    after = result.receipt['randomness']['state_after']['seed_sequence']
    assert before['n_children_spawned'] == 0
    assert after['n_children_spawned'] == 1
    assert result.receipt == ch.replay(tmp_path / 'qmc').receipt


@pytest.mark.parametrize('array', [np.zeros(3), np.zeros(64, dtype=np.int64), np.full(64, 100.0)])
def test_backend_contract_violations_cannot_publish(monkeypatch, tmp_path, array):
    monkeypatch.setattr('chances._operations.execute_operation', lambda *args: array)
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(spec('uniform', {'size': 64}), output=tmp_path / 'invalid')
    assert error.value.code == 'CONTRACT_VIOLATION'
    assert not (tmp_path / 'invalid').exists()


def test_special_json_files_fail_without_reading(tmp_path):
    import os

    if not hasattr(os, 'mkfifo'):
        pytest.skip('named pipes unavailable')
    path = tmp_path / 'recipe.json'
    os.mkfifo(path)
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(path)
    assert error.value.code == 'INVALID_JSON'


def test_sources_preserve_identifiers_and_reject_implicit_precision_loss():
    source = ['001', '002', '003']
    result = ch.generate(spec('permutation', {}), source=source)
    assert set(result.data.tolist()) == set(source)
    assert source == ['001', '002', '003']
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec('shuffle', {}), source=[9007199254740993, 1.0])
    assert error.value.code == 'LOSSY_SOURCE'
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec('shuffle', {}), source=['001', 2])
    assert error.value.code == 'INVALID_SOURCE'


def test_literal_sources_do_not_invoke_array_callbacks():
    called = []

    class Arbitrary:
        def __array__(self, *args, **kwargs):
            called.append(True)
            return np.array(42)

    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec('shuffle', {}), source=[Arbitrary()])
    assert error.value.code == 'INVALID_SOURCE'
    assert called == []


def test_masked_source_cannot_silently_lose_missingness():
    masked = np.ma.array([1, 999], mask=[False, True])
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec('choice', {'size': 2}), source=masked)
    assert error.value.code == 'INVALID_SOURCE'


def test_source_byte_limit_is_checked_before_array_allocation(monkeypatch):
    recipe = spec('choice', {'size': 1})
    recipe['limits'] = {'max_bytes': 16}
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(recipe, source=['x' * 100])
    assert error.value.code == 'RESOURCE_LIMIT'


@pytest.mark.parametrize(
    'operation,parameters,array',
    [
        ('balanced_allocation', {'counts': [2, 2]}, np.zeros(4, dtype=np.int64)),
        (
            'stratified_split',
            {'groups': ['a', 'a', 'b', 'b'], 'counts': [[1, 1], [1, 1]]},
            np.arange(4, dtype=np.int64),
        ),
        (
            'bootstrap',
            {'n': 4, 'resamples': 1, 'sample_size': 4, 'mode': 'cluster', 'groups': [0, 0, 1, 1]},
            np.array([[0, 2, 1, 3]], dtype=np.int64),
        ),
        ('antithetic', {'n': 4, 'd': 1}, np.array([[1.0], [2.0], [1.0], [2.0]])),
        ('sobol', {'n': 4, 'd': 2}, np.zeros((4, 2))),
        (
            'distribution',
            {
                'distribution': 'mixture',
                'size': 8,
                'components': [
                    {'distribution': 'bernoulli', 'p': 1},
                    {'distribution': 'bernoulli', 'p': 0},
                ],
                'weights': [0, 1],
            },
            np.ones(8),
        ),
        (
            'distribution',
            {'distribution': 'multinomial', 'size': 1, 'n': 2**63 - 1, 'p': [1, 0, 0]},
            np.full((1, 3), 2**63 - 1, dtype=np.int64),
        ),
    ],
)
def test_plausible_but_structurally_wrong_results_fail(
    monkeypatch, tmp_path, operation, parameters, array
):
    monkeypatch.setattr('chances._operations.execute_operation', lambda *args: array)
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(spec(operation, parameters), output=tmp_path / 'invalid-structure')
    assert error.value.code == 'CONTRACT_VIOLATION'
    assert not (tmp_path / 'invalid-structure').exists()


@pytest.mark.parametrize('state_field', ['state_before', 'state_after'])
def test_incomplete_rng_provenance_is_not_a_valid_receipt(tmp_path, state_field):
    bundle = tmp_path / 'incomplete'
    ch.generate(spec(), output=bundle)
    path = bundle / 'receipt.json'
    value = json.loads(path.read_text())
    value['randomness'][state_field] = {}
    value['receipt_sha256'] = _json_hash({k: v for k, v in value.items() if k != 'receipt_sha256'})
    path.write_text(json.dumps(value))
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


def test_initial_rng_state_cannot_disagree_with_its_declared_seed(tmp_path):
    bundle = tmp_path / 'wrong-state'
    ch.generate(spec(), output=bundle)
    path = bundle / 'receipt.json'
    value = json.loads(path.read_text())
    value['randomness']['state_before']['state']['state'] += 1
    value['receipt_sha256'] = _json_hash({k: v for k, v in value.items() if k != 'receipt_sha256'})
    path.write_text(json.dumps(value))
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'
