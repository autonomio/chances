"""The JSON CLI must expose the same checked protocol and artifact failures."""

import json

import numpy as np
import pytest

import chances as ch
from chances.__main__ import main


def normal_recipe():
    return {'operation': 'normal', 'parameters': {'size': 4}, 'randomness': {'seed': 42}}


def test_catalog_command_is_machine_readable_and_draws_nothing(capsys, monkeypatch):
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    assert main(['catalog']) == 0
    captured = capsys.readouterr()
    assert captured.err == ''
    result = json.loads(captured.out)
    assert result == ch.catalog()
    assert {'normal', 'bootstrap', 'sobol'} <= result['operations'].keys()


def test_inspect_command_resolves_sources_without_drawing(tmp_path, capsys, monkeypatch):
    spec = tmp_path / 'recipe.json'
    spec.write_text(json.dumps({'operation': 'shuffle', 'randomness': {'seed': 9}}))
    source = tmp_path / 'source.npy'
    np.save(source, np.arange(12).reshape(4, 3))
    monkeypatch.setattr('chances._api.generator', lambda *args: pytest.fail('RNG created'))
    assert main(['inspect', str(spec), '--source', str(source)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ''
    result = json.loads(captured.out)
    assert result == ch.inspect(spec, source=source)
    assert result['source']['shape'] == [4, 3]
    assert result['output']['shape'] == [4, 3]
    assert result['resolved_spec']['randomness']['stream'] == 'default'


def test_cli_generate_verify_and_replay_bind_identical_receipts(tmp_path, capsys):
    spec = tmp_path / 'recipe.json'
    spec.write_text(json.dumps(normal_recipe()))
    bundle = tmp_path / 'generated'
    assert main(['generate', str(spec), '--output', str(bundle)]) == 0
    generated = capsys.readouterr()
    assert generated.err == ''
    generated_json = json.loads(generated.out)
    assert generated_json['output'] == str(bundle)
    assert main(['verify', str(bundle)]) == 0
    verified = capsys.readouterr()
    assert verified.err == ''
    assert json.loads(verified.out) == {'verified': True, 'receipt': generated_json['receipt']}
    retry = tmp_path / 'retry'
    assert main(['replay', str(bundle), '--output', str(retry)]) == 0
    replayed = capsys.readouterr()
    assert replayed.err == ''
    assert json.loads(replayed.out) == json.loads(verified.out)
    np.testing.assert_array_equal(
        np.load(bundle / 'data.npy', allow_pickle=False),
        np.load(retry / 'data.npy', allow_pickle=False),
    )
    assert main(['replay', str(bundle)]) == 0
    assert json.loads(capsys.readouterr().out)['receipt'] == generated_json['receipt']


def test_cli_source_rows_remain_observations_and_are_snapshotted(tmp_path, capsys):
    spec = tmp_path / 'recipe.json'
    spec.write_text(
        json.dumps(
            {
                'operation': 'choice',
                'parameters': {'size': 2, 'replace': False},
                'randomness': {'seed': 7},
            }
        )
    )
    source = tmp_path / 'source.npy'
    observations = np.array([[11, 12], [21, 22], [31, 32]])
    np.save(source, observations)
    bundle = tmp_path / 'selected'
    assert main(['generate', str(spec), '--source', str(source), '--output', str(bundle)]) == 0
    receipt = json.loads(capsys.readouterr().out)['receipt']
    assert receipt['source']['shape'] == [3, 2]
    assert receipt['output']['shape'] == [2, 2]
    result = ch.verify(bundle)
    assert set(map(tuple, result.data)) <= set(map(tuple, observations))
    assert len(set(map(tuple, result.data))) == 2
    np.testing.assert_array_equal(np.load(bundle / 'source.npy', allow_pickle=False), observations)


@pytest.mark.parametrize('command', ['inspect', 'generate'])
def test_cli_protocol_errors_use_stderr_json_and_nonzero_exit(tmp_path, capsys, command):
    spec = tmp_path / 'missing-seed.json'
    spec.write_text(json.dumps({'operation': 'normal'}))
    argv = [command, str(spec)]
    if command == 'generate':
        argv.extend(['--output', str(tmp_path / 'never-published')])
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    error = json.loads(captured.err)['error']
    assert error['code'] == 'SEED_REQUIRED'
    assert error['details'] == {}
    assert 'seed' in error['message']
    assert not (tmp_path / 'never-published').exists()


@pytest.mark.parametrize('command', ['verify', 'replay'])
def test_cli_missing_artifact_errors_are_structured(tmp_path, capsys, command):
    assert main([command, str(tmp_path / 'missing')]) == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    assert json.loads(captured.err)['error']['code'] == 'INVALID_BUNDLE'


def test_cli_repeated_destination_preserves_existing_bundle(tmp_path, capsys):
    spec = tmp_path / 'recipe.json'
    spec.write_text(json.dumps(normal_recipe()))
    bundle = tmp_path / 'existing'
    argv = ['generate', str(spec), '--output', str(bundle)]
    assert main(argv) == 0
    receipt = json.loads(capsys.readouterr().out)['receipt']
    before = {path.name: path.read_bytes() for path in bundle.iterdir()}
    assert main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    assert json.loads(captured.err)['error']['code'] == 'OUTPUT_EXISTS'
    assert {path.name: path.read_bytes() for path in bundle.iterdir()} == before
    assert ch.verify(bundle).receipt == receipt


@pytest.mark.parametrize('argv', [[], ['unknown'], ['generate', 'recipe.json'], ['verify']])
def test_cli_syntax_errors_remain_argparse_failures(capsys, argv):
    with pytest.raises(SystemExit) as error:
        main(argv)
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    assert 'usage: chances' in captured.err
