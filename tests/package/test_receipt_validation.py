"""Consistently rehashed artifacts still need valid scientific and RNG contracts."""

import hashlib
import json

import numpy as np
import pytest

import chances as ch

ENGINES = ['pcg64dxsm', 'pcg64', 'philox', 'sfc64', 'mt19937']
DELETE = object()


def recipe(engine='pcg64dxsm'):
    return {
        'operation': 'normal',
        'parameters': {'size': 4},
        'randomness': {'seed': 42, 'stream': 'receipt-boundary', 'engine': engine},
    }


def digest(value):
    # Independent JSON hashing keeps corruption tests beyond the outer checksum gate.
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')
    )
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def alter_receipt(bundle, path, value, *, update_recipe=False):
    receipt_path = bundle / 'receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    target = receipt
    for key in path[:-1]:
        target = target[key]
    if value is DELETE:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    if update_recipe:
        receipt['spec_sha256'] = digest(receipt['spec'])
        (bundle / 'recipe.json').write_text(json.dumps(receipt['spec']), encoding='utf-8')
    receipt['receipt_sha256'] = digest(
        {key: item for key, item in receipt.items() if key != 'receipt_sha256'}
    )
    receipt_path.write_text(json.dumps(receipt), encoding='utf-8')


@pytest.mark.parametrize(
    'field,value',
    [('receipt_version', True), ('receipt_version', 2), ('contract', DELETE), ('unexpected', 1)],
)
def test_rehashed_receipts_cannot_change_schema(tmp_path, field, value):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, [field], value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


@pytest.mark.parametrize('value', [False, DELETE])
def test_receipt_must_attest_every_required_check(tmp_path, value):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, ['checks', 'declared_support'], value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


def test_saved_contract_cannot_disagree_with_resolved_operation(tmp_path):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, ['contract', 'shape'], [2, 2])
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


def test_saved_recipe_must_already_include_default_parameters(tmp_path):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, ['spec', 'parameters', 'loc'], DELETE, update_recipe=True)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


@pytest.mark.parametrize(
    'field,value',
    [
        ('seed', 43),
        ('stream', 'different'),
        ('engine', 'philox'),
        ('derivation', 'unknown'),
        ('state_after', []),
        ('state_before', DELETE),
    ],
)
def test_rng_provenance_must_match_declared_stream(tmp_path, field, value):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, ['randomness', field], value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


@pytest.mark.parametrize('engine', ENGINES)
@pytest.mark.parametrize(
    'field,value', [('pool_size', 8), ('n_children_spawned', 2**32), ('spawn_key', [1])]
)
def test_all_engines_reject_inconsistent_seed_sequence_provenance(tmp_path, engine, field, value):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(engine), output=bundle)
    alter_receipt(bundle, ['randomness', 'state_after', 'seed_sequence', field], value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


def test_seed_sequence_entropy_must_bind_the_declared_seed(tmp_path):
    bundle = tmp_path / 'bundle'
    result = ch.generate(recipe(), output=bundle)
    entropy = result.receipt['randomness']['state_after']['seed_sequence']['entropy']
    alter_receipt(
        bundle,
        ['randomness', 'state_after', 'seed_sequence', 'entropy'],
        [entropy[0] + 1, *entropy[1:]],
    )
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


@pytest.mark.parametrize(
    'engine,path,value',
    [
        ('pcg64dxsm', ['state', 'state'], 2**128),
        ('pcg64', ['has_uint32'], 2),
        ('pcg64', ['has_uint32'], True),
        ('philox', ['buffer_pos'], 5),
        ('philox', ['state', 'counter'], [0, 0, 0]),
        ('sfc64', ['state', 'state'], [2**64, 0, 0, 0]),
        ('mt19937', ['state', 'pos'], 625),
        ('mt19937', ['state', 'key'], [0] * 624),
        ('pcg64dxsm', ['bit_generator'], 'PCG64'),
    ],
)
def test_invalid_engine_state_cannot_be_laundered_by_rehashing(tmp_path, engine, path, value):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(engine), output=bundle)
    if engine == 'mt19937' and path == ['state', 'key']:
        value = [2**32, *value[1:]]
    alter_receipt(bundle, ['randomness', 'state_after', *path], value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


@pytest.mark.parametrize(
    'path,value',
    [
        (['versions', 'numpy'], ''),
        (['versions', 'scipy'], 1),
        (['versions', 'chances'], DELETE),
        (['environment', 'machine'], DELETE),
        (['environment', 'unexpected'], 'x'),
    ],
)
def test_complete_implementation_envelope_is_required(tmp_path, path, value):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, path, value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


def test_valid_old_implementation_is_verifiable_but_not_replayable(tmp_path):
    bundle = tmp_path / 'bundle'
    result = ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, ['versions', 'numpy'], 'recorded-other-version')
    np.testing.assert_array_equal(ch.verify(bundle).data, result.data)
    retry = tmp_path / 'retry'
    with pytest.raises(ch.ChancesError) as error:
        ch.replay(bundle, output=retry)
    assert error.value.code == 'REPLAY_INCOMPATIBLE'
    assert not retry.exists()


@pytest.mark.parametrize('change', ['extra', 'missing', 'directory', 'source-declaration'])
def test_bundle_inventory_is_exact(tmp_path, change):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    if change == 'extra':
        (bundle / 'notes.txt').write_text('extra', encoding='utf-8')
    elif change == 'missing':
        (bundle / 'data.npy').unlink()
    elif change == 'directory':
        (bundle / 'data.npy').unlink()
        (bundle / 'data.npy').mkdir()
    else:
        np.save(bundle / 'source.npy', np.arange(4))
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_BUNDLE'


def test_declared_source_snapshot_must_exist(tmp_path):
    bundle = tmp_path / 'bundle'
    ch.generate(
        {'operation': 'shuffle', 'randomness': {'seed': 42}}, source=np.arange(4), output=bundle
    )
    (bundle / 'source.npy').unlink()
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_BUNDLE'


def test_bundle_directory_symlinks_are_rejected(tmp_path):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alias = tmp_path / 'alias'
    alias.symlink_to(bundle, target_is_directory=True)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(alias)
    assert error.value.code == 'INVALID_BUNDLE'


def test_replay_detects_consistently_rehashed_but_different_plausible_values(tmp_path):
    bundle = tmp_path / 'bundle'
    result = ch.generate(recipe(), output=bundle)
    changed = result.data + 0.125
    np.save(bundle / 'data.npy', changed, allow_pickle=False)
    header = json.dumps(
        {'dtype': changed.dtype.str, 'shape': list(changed.shape)},
        sort_keys=True,
        separators=(',', ':'),
    )
    content_digest = hashlib.sha256(
        b'chances-array-v1\x00' + header.encode('utf-8') + b'\x00' + changed.tobytes(order='C')
    ).hexdigest()
    alter_receipt(bundle, ['output', 'sha256'], content_digest)
    # Verification proves consistency, not authorship of an unsigned receipt.
    np.testing.assert_array_equal(ch.verify(bundle).data, changed)
    retry = tmp_path / 'retry'
    with pytest.raises(ch.ChancesError) as error:
        ch.replay(bundle, output=retry)
    assert error.value.code == 'REPLAY_MISMATCH'
    assert not retry.exists()


@pytest.mark.parametrize(
    'path,value,code',
    [
        (['checks', 'finite'], 1, 'INVALID_RECEIPT'),
        (['contract', 'shape'], [True], 'INVALID_RECEIPT'),
        (['output', 'shape'], [True], 'INTEGRITY_MISMATCH'),
        (['output', 'values'], True, 'INTEGRITY_MISMATCH'),
        (['randomness', 'seed'], True, 'INVALID_RECEIPT'),
        (['spec', 'randomness', 'seed'], True, 'INTEGRITY_MISMATCH'),
    ],
)
def test_rehashed_receipts_cannot_alias_boolean_and_integer_fields(tmp_path, path, value, code):
    bundle = tmp_path / 'bundle'
    ch.generate(
        {'operation': 'normal', 'parameters': {'size': 1}, 'randomness': {'seed': 1}}, output=bundle
    )
    alter_receipt(bundle, path, value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == code


@pytest.mark.parametrize('field,value', [('shape', [True]), ('values', True)])
def test_source_metadata_requires_integer_counts_not_boolean_aliases(tmp_path, field, value):
    bundle = tmp_path / 'bundle'
    ch.generate(
        {'operation': 'shuffle', 'randomness': {'seed': 1}}, source=np.array([42]), output=bundle
    )
    alter_receipt(bundle, ['source', field], value)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INTEGRITY_MISMATCH'
    assert error.value.details['role'] == 'source'


def test_saved_resolved_parameters_preserve_canonical_numeric_types(tmp_path):
    bundle = tmp_path / 'bundle'
    ch.generate(recipe(), output=bundle)
    alter_receipt(bundle, ['spec', 'parameters', 'loc'], 0, update_recipe=True)
    with pytest.raises(ch.ChancesError) as error:
        ch.verify(bundle)
    assert error.value.code == 'INVALID_RECEIPT'


def test_replay_envelope_does_not_alias_integer_and_float_metadata(tmp_path):
    bundle = tmp_path / 'bundle'
    result = ch.generate(recipe(), output=bundle)
    cpu_count = result.receipt['environment']['cpu_count']
    assert type(cpu_count) is int
    alter_receipt(bundle, ['environment', 'cpu_count'], float(cpu_count))
    np.testing.assert_array_equal(ch.verify(bundle).data, result.data)
    with pytest.raises(ch.ChancesError) as error:
        ch.replay(bundle, output=tmp_path / 'never-published')
    assert error.value.code == 'REPLAY_INCOMPATIBLE'
    assert not (tmp_path / 'never-published').exists()
