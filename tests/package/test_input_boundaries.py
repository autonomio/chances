"""Literal protocols and native observations must never execute input callbacks."""

from pathlib import Path

import numpy as np
import pytest

import chances as ch


def recipe(operation='normal', parameters=None):
    return {
        'operation': operation,
        'parameters': {'size': 4} if parameters is None else parameters,
        'randomness': {'seed': 7, 'stream': 'boundary'},
    }


@pytest.mark.parametrize(
    'placement', ['root', 'parameters', 'list', 'tuple', 'str', 'int', 'float', 'key']
)
def test_json_subclasses_are_rejected_without_running_callbacks(placement):
    called = []

    class Mapping(dict):
        def items(self):
            called.append('items')
            return super().items()

    class Sequence(list):
        def __iter__(self):
            called.append('iterate')
            return super().__iter__()

    class Tuple(tuple):
        def __iter__(self):
            called.append('iterate tuple')
            return super().__iter__()

    class Text(str):
        def encode(self, *args, **kwargs):
            called.append('encode')
            return super().encode(*args, **kwargs)

    class Integer(int):
        def __int__(self):
            called.append('integer')
            return super().__int__()

    class Real(float):
        def __float__(self):
            called.append('float')
            return super().__float__()

    spec = recipe()
    if placement == 'root':
        spec = Mapping(spec)
    elif placement == 'parameters':
        spec['parameters'] = Mapping(size=4)
    elif placement == 'key':
        spec['parameters'] = {Text('size'): 4}
    else:
        spec['parameters']['size'] = {
            'list': Sequence([4]),
            'tuple': Tuple((4,)),
            'str': Text('4'),
            'int': Integer(4),
            'float': Real(4),
        }[placement]
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec)
    assert error.value.code == 'INVALID_JSON'
    assert called == []


def test_native_tuples_are_normalized_to_json_lists():
    profile = ch.inspect(recipe(parameters={'size': (2, 3)}))
    assert profile['resolved_spec']['parameters']['size'] == [2, 3]
    assert profile['output']['shape'] == [2, 3]
    assert ch.generate(profile['resolved_spec']).data.shape == (2, 3)


def test_numpy_scalar_subclass_cannot_execute_item_callback():
    called = []

    class CallbackScalar(np.float64):
        def item(self, *args):
            called.append('item')
            return 1.25

    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(recipe('shuffle', {}), source=[CallbackScalar(1.25)])
    assert error.value.code == 'INVALID_SOURCE'
    assert called == []


@pytest.mark.parametrize('placement,code', [('spec', 'INVALID_SPEC'), ('source', 'INVALID_SOURCE')])
def test_path_subclasses_do_not_execute_fspath(placement, code):
    called = []

    class CallbackPath(type(Path())):
        def __fspath__(self):
            called.append('fspath')
            return super().__fspath__()

    value = CallbackPath('unread-input.npy')
    with pytest.raises(ch.ChancesError) as error:
        if placement == 'spec':
            ch.inspect(value)
        else:
            ch.inspect(recipe('shuffle', {}), source=value)
    assert error.value.code == code
    assert called == []


@pytest.mark.parametrize(
    'source',
    [
        [np.int64(10), np.int64(20)],
        [np.float64(1.25), np.float64(2.5)],
        [np.bool_(True), np.bool_(False)],
        [np.str_('001'), np.str_('002')],
        [np.bytes_(b'001'), np.bytes_(b'002')],
    ],
)
def test_native_numpy_scalars_preserve_observation_values(source):
    result = ch.generate(recipe('permutation', {}), source=source)
    assert sorted(result.data.tolist()) == sorted(np.asarray(source).tolist())
    assert result.data.dtype == np.asarray(source).dtype
    assert result.receipt['source']['shape'] == [2]


@pytest.mark.parametrize(
    'raw',
    [b'{"operation":"normal","operation":"uniform"}', b'{"parameters":{"size":1,"size":2}}'],
)
def test_duplicate_json_fields_fail_before_rng(tmp_path, monkeypatch, raw):
    path = tmp_path / 'duplicate.json'
    path.write_bytes(raw)
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(path)
    assert error.value.code == 'INVALID_JSON'
    assert error.value.details['field'] in {'operation', 'size'}


@pytest.mark.parametrize('raw', [b'\xff', b'{', b'{"randomness":{"seed":NaN}}'])
def test_invalid_file_json_is_structured_failure(tmp_path, raw):
    path = tmp_path / 'invalid.json'
    path.write_bytes(raw)
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(path)
    assert error.value.code == 'INVALID_JSON'


def test_protocol_document_limit_is_checked_before_execution(tmp_path, monkeypatch):
    path = tmp_path / 'too-large.json'
    path.write_bytes(b' ' * (1_048_576 + 1))
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(path)
    assert error.value.code == 'RESOURCE_LIMIT'


def test_json_symbolic_links_are_rejected(tmp_path):
    original = tmp_path / 'recipe.json'
    original.write_text('{}', encoding='utf-8')
    link = tmp_path / 'link.json'
    link.symlink_to(original)
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(link)
    assert error.value.code == 'INVALID_JSON'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), '\ud800'])
def test_nonfinite_and_non_utf8_protocol_values_fail(value):
    spec = recipe()
    spec['parameters']['size'] = value
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec)
    assert error.value.code == 'INVALID_JSON'


def test_recursive_protocol_is_rejected_without_recursing_forever():
    spec = recipe()
    spec['parameters']['recursive'] = spec
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec)
    assert error.value.code == 'INVALID_JSON'


@pytest.mark.parametrize(
    'limits', [None, [], {'unknown': 1}, {'max_work': True}, {'max_bytes': 2**63}]
)
def test_invalid_limits_do_not_create_rng(monkeypatch, limits):
    spec = recipe()
    spec['limits'] = limits
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(spec)
    assert error.value.code == 'INVALID_LIMITS'


@pytest.mark.parametrize(
    'source,code',
    [
        ([[1], [2, 3]], 'INVALID_SOURCE'),
        (np.zeros((1,) * 17), 'UNSUPPORTED_DTYPE'),
        (np.array([1 + 2j]), 'UNSUPPORTED_DTYPE'),
        (np.array(['2020-01-01'], dtype='datetime64[D]'), 'UNSUPPORTED_DTYPE'),
        (np.array([float('nan')]), 'INVALID_SOURCE'),
        ([True, 1], 'INVALID_SOURCE'),
    ],
)
def test_ambiguous_or_unsupported_sources_fail_before_rng(monkeypatch, source, code):
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(recipe('shuffle', {}), source=source)
    assert error.value.code == code


def test_deep_source_sequences_are_rejected():
    source = 1
    for _ in range(17):
        source = [source]
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(recipe('shuffle', {}), source=source)
    assert error.value.code == 'INVALID_SOURCE'


@pytest.mark.parametrize('source', [[1, 2, 3], np.arange(3)])
def test_source_value_budget_covers_sequences_and_arrays(source):
    spec = recipe('shuffle', {})
    spec['limits'] = {'max_values': 2}
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec, source=source)
    assert error.value.code == 'RESOURCE_LIMIT'


@pytest.mark.parametrize('filename', ['corrupt.npy', 'array.npz'])
def test_npy_input_requires_a_single_readable_array(tmp_path, filename):
    path = tmp_path / filename
    path.write_bytes(b'not a NumPy artifact')
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(recipe('shuffle', {}), source=path)
    assert error.value.code == 'INVALID_SOURCE'


def test_oversized_npy_is_rejected_before_loading(tmp_path, monkeypatch):
    path = tmp_path / 'large.npy'
    path.write_bytes(b'x' * 65_553)
    spec = recipe('shuffle', {})
    spec['limits'] = {'max_bytes': 16}
    monkeypatch.setattr(np, 'load', lambda *args, **kwargs: pytest.fail('NPY loaded'))
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(spec, source=path)
    assert error.value.code == 'RESOURCE_LIMIT'


def test_source_file_change_during_snapshot_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / 'source.npy'
    np.save(path, np.arange(4))
    hashes = iter(['before', 'after'])
    monkeypatch.setattr('chances._api._file_hash', lambda *args: next(hashes))
    with pytest.raises(ch.ChancesError) as error:
        ch.inspect(recipe('shuffle', {}), source=path)
    assert error.value.code == 'SOURCE_CHANGED'


def test_path_source_is_archived_independently_of_later_file_changes(tmp_path):
    source = tmp_path / 'source.npy'
    observations = np.array([[10, 11], [20, 21], [30, 31]], dtype=np.int64)
    np.save(source, observations)
    bundle = tmp_path / 'bundle'
    result = ch.generate(recipe('shuffle', {}), source=source, output=bundle)
    np.save(source, np.full_like(observations, -1))
    archived = np.load(bundle / 'source.npy', allow_pickle=False)
    np.testing.assert_array_equal(archived, observations)
    np.testing.assert_array_equal(ch.replay(bundle).data, result.data)


@pytest.mark.parametrize(
    'operation', ['write', 'generate-output', 'verify', 'replay', 'replay-output']
)
@pytest.mark.parametrize('kind', ['pathlike', 'path-subclass'])
def test_artifact_paths_reject_callback_objects(tmp_path, operation, kind):
    called = []
    bundle = tmp_path / 'bundle'
    result = ch.generate(recipe(), output=bundle)

    class CallbackPathLike:
        def __init__(self, value):
            self.value = value

        def __fspath__(self):
            called.append('fspath')
            return str(self.value)

    class CallbackPath(type(Path())):
        def __getattribute__(self, name):
            if name in {'_raw_paths', '_parts', '_flavour'}:
                called.append('path attribute')
            return super().__getattribute__(name)

    target = bundle if operation in {'verify', 'replay'} else tmp_path / 'never-published'
    callback = CallbackPathLike(target) if kind == 'pathlike' else CallbackPath(target)
    called.clear()
    with pytest.raises(ch.ChancesError) as error:
        if operation == 'write':
            result.write(callback)
        elif operation == 'generate-output':
            ch.generate(recipe(), output=callback)
        elif operation == 'verify':
            ch.verify(callback)
        elif operation == 'replay':
            ch.replay(callback)
        else:
            ch.replay(bundle, output=callback)
    expected = 'INVALID_BUNDLE' if operation in {'verify', 'replay'} else 'OUTPUT_FAILED'
    assert error.value.code == expected
    assert called == []
    assert not (tmp_path / 'never-published').exists()
    assert list(tmp_path.iterdir()) == [bundle]
    assert ch.verify(bundle).receipt == result.receipt
