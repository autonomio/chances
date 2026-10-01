"""Failed execution or publication must leave no plausible scientific artifact."""

import numpy as np
import pytest

import chances as ch
import chances._api as api


def recipe(operation='normal', parameters=None):
    return {
        'operation': operation,
        'parameters': {'size': 4} if parameters is None else parameters,
        'randomness': {'seed': 42},
    }


@pytest.mark.parametrize('limits,required', [({'max_bytes': 96}, 128), ({'max_work': 8}, 16)])
def test_verification_resources_are_reserved_before_drawing(monkeypatch, limits, required):
    spec = recipe()
    spec['limits'] = limits
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(spec)
    assert error.value.code == 'RESOURCE_LIMIT'
    assert error.value.details['phase'] == 'postconditions'
    assert error.value.details['required'] == required


@pytest.mark.parametrize(
    'failure',
    [
        ValueError('invalid backend'),
        TypeError('invalid backend'),
        OverflowError('invalid backend'),
        np.linalg.LinAlgError('singular'),
    ],
)
def test_numerical_execution_errors_cannot_publish(monkeypatch, tmp_path, failure):
    def fail(*args):
        raise failure

    monkeypatch.setattr('chances._operations.execute_operation', fail)
    destination = tmp_path / 'failed'
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(recipe(), output=destination)
    assert error.value.code == 'OPERATION_FAILED'
    assert error.value.details['operation'] == 'normal'
    assert not destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_declared_sampling_failure_is_preserved_without_substitution(monkeypatch, tmp_path):
    failure = ch.ChancesError(
        'SAMPLING_EXHAUSTED', 'Declared trial budget exhausted.', {'trials': 2}
    )

    def fail(*args):
        raise failure

    monkeypatch.setattr('chances._operations.execute_operation', fail)
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(recipe(), output=tmp_path / 'failed')
    assert error.value is failure
    assert error.value.to_dict()['details'] == {'trials': 2}
    assert list(tmp_path.iterdir()) == []


def test_validation_backend_errors_are_reported_before_rng(monkeypatch):
    def fail(*args):
        raise ValueError('invalid domain')

    monkeypatch.setattr('chances._operations.resolve_operation', fail)
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(recipe())
    assert error.value.code == 'INVALID_PARAMETERS'
    assert error.value.details == {'operation': 'normal', 'error': 'invalid domain'}


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_backend_results_cannot_publish(monkeypatch, tmp_path, value):
    monkeypatch.setattr('chances._operations.execute_operation', lambda *args: np.full(4, value))
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(recipe(), output=tmp_path / 'failed')
    assert error.value.code == 'NONFINITE_RESULT'
    assert error.value.details == {'role': 'output'}
    assert list(tmp_path.iterdir()) == []


def test_without_replacement_respects_duplicate_observation_multiplicity(monkeypatch):
    source = np.array([[10, 11], [10, 11], [20, 21]])
    spec = recipe('choice', {'size': 3, 'replace': False})
    valid = np.array([[10, 11], [20, 21], [10, 11]])
    monkeypatch.setattr('chances._operations.execute_operation', lambda *args: valid)
    np.testing.assert_array_equal(ch.generate(spec, source=source).data, valid)
    monkeypatch.setattr(
        'chances._operations.execute_operation', lambda *args: np.repeat(source[:1], 3, axis=0)
    )
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(spec, source=source)
    assert error.value.code == 'CONTRACT_VIOLATION'
    assert 'beyond availability' in str(error.value)


def test_busy_destination_preserves_other_writer_lock(tmp_path):
    result = ch.generate(recipe())
    lock = tmp_path / 'busy.chances-lock'
    lock.write_bytes(b'other writer')
    with pytest.raises(ch.ChancesError) as error:
        result.write(tmp_path / 'busy')
    assert error.value.code == 'OUTPUT_BUSY'
    assert lock.read_bytes() == b'other writer'
    assert not (tmp_path / 'busy').exists()


def test_lock_failure_is_structured_and_does_not_stage(tmp_path, monkeypatch):
    result = ch.generate(recipe())

    def fail(*args):
        raise OSError('permission denied')

    monkeypatch.setattr(api.os, 'open', fail)
    with pytest.raises(ch.ChancesError) as error:
        result.write(tmp_path / 'failed')
    assert error.value.code == 'OUTPUT_FAILED'
    assert list(tmp_path.iterdir()) == []


def test_destination_race_preserves_competing_artifacts_and_removes_staging(tmp_path, monkeypatch):
    result = ch.generate(recipe())
    destination = tmp_path / 'competing'
    verify = api.verify

    def competing_writer(path):
        verified = verify(path)
        destination.mkdir()
        (destination / 'owned-by-other-writer').write_bytes(b'preserve')
        return verified

    monkeypatch.setattr(api, 'verify', competing_writer)
    with pytest.raises(ch.ChancesError) as error:
        result.write(destination)
    assert error.value.code == 'OUTPUT_EXISTS'
    assert (destination / 'owned-by-other-writer').read_bytes() == b'preserve'
    assert list(tmp_path.iterdir()) == [destination]


def test_rename_failure_removes_all_staged_artifacts(tmp_path, monkeypatch):
    result = ch.generate(recipe())

    def fail(*args):
        raise OSError('rename refused')

    monkeypatch.setattr(api.os, 'rename', fail)
    with pytest.raises(ch.ChancesError) as error:
        result.write(tmp_path / 'failed')
    assert error.value.code == 'OUTPUT_FAILED'
    assert list(tmp_path.iterdir()) == []
