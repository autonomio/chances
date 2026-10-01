"""Native publication cannot replace a racing destination or expose partial output."""

import ctypes
import errno
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import chances as ch
import chances._api as api
import chances._publication as publication
from chances.__main__ import main


def recipe():
    return {'operation': 'normal', 'parameters': {'size': 4}, 'randomness': {'seed': 42}}


@pytest.mark.parametrize('kind', ['empty_directory', 'directory', 'file', 'symlink'])
def test_atomic_publish_rejects_destination_created_after_last_check(tmp_path, monkeypatch, kind):
    if kind == 'symlink' and sys.platform == 'win32':
        pytest.skip('Creating Windows symlinks requires separate host privileges.')
    result = ch.generate(recipe())
    destination = tmp_path / 'racing'
    publish = api.publish_directory
    competing_inode = []

    def competing_writer(source, target):
        assert target == destination
        assert not destination.exists()
        if kind in ('empty_directory', 'directory'):
            destination.mkdir()
            if kind == 'directory':
                (destination / 'other-writer').write_bytes(b'preserve')
        elif kind == 'file':
            destination.write_bytes(b'preserve')
        else:
            destination.symlink_to('unrelated-target')
        competing_inode.append(destination.lstat().st_ino)
        publish(source, target)

    monkeypatch.setattr(api, 'publish_directory', competing_writer)
    with pytest.raises(ch.ChancesError) as error:
        result.write(destination)
    assert error.value.code == 'OUTPUT_EXISTS'
    assert destination.lstat().st_ino == competing_inode[0]
    assert list(tmp_path.iterdir()) == [destination]
    if kind == 'empty_directory':
        assert list(destination.iterdir()) == []
    elif kind == 'directory':
        assert (destination / 'other-writer').read_bytes() == b'preserve'
    elif kind == 'file':
        assert destination.read_bytes() == b'preserve'
    else:
        assert destination.is_symlink()
        assert str(destination.readlink()) == 'unrelated-target'


@pytest.mark.parametrize('action', ['write', 'generate'])
def test_output_parent_file_produces_structured_error_without_mutation(tmp_path, action):
    parent = tmp_path / 'existing-file'
    parent.write_bytes(b'preserve')
    destination = parent / 'bundle'
    with pytest.raises(ch.ChancesError) as error:
        if action == 'write':
            ch.generate(recipe()).write(destination)
        else:
            ch.generate(recipe(), output=destination)
    assert error.value.code == 'OUTPUT_FAILED'
    assert error.value.details['path'] == str(destination)
    assert parent.read_bytes() == b'preserve'
    assert list(tmp_path.iterdir()) == [parent]


def test_cli_output_parent_file_reports_json_and_error_exit(tmp_path, capsys):
    specification = tmp_path / 'recipe.json'
    specification.write_text(json.dumps(recipe()))
    parent = tmp_path / 'existing-file'
    parent.write_bytes(b'preserve')
    code = main(['generate', str(specification), '--output', str(parent / 'bundle')])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ''
    assert json.loads(captured.err)['error']['code'] == 'OUTPUT_FAILED'
    assert parent.read_bytes() == b'preserve'
    assert set(tmp_path.iterdir()) == {parent, specification}


@pytest.mark.parametrize('platform', ['linux', 'darwin'])
@pytest.mark.parametrize('code', [errno.EEXIST, errno.ENOSYS, errno.EINVAL])
def test_native_errno_is_preserved_without_plain_rename_fallback(
    tmp_path, monkeypatch, platform, code
):
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.mkdir()
    calls = []

    def failed(*arguments):
        calls.append(arguments)
        ctypes.set_errno(code)
        return -1

    def native(name, arguments):
        assert name == ('renameat2' if platform == 'linux' else 'renamex_np')
        assert len(arguments) == (5 if platform == 'linux' else 3)
        return failed

    monkeypatch.setattr(publication.sys, 'platform', platform)
    monkeypatch.setattr(publication, '_rename_function', native)
    monkeypatch.setattr(publication.os, 'rename', lambda *args: pytest.fail('unsafe fallback'))
    expected = FileExistsError if code == errno.EEXIST else OSError
    with pytest.raises(expected) as error:
        publication.publish_directory(source, target)
    assert error.value.errno == code
    if platform == 'linux':
        assert calls == [(-100, bytes(source), -100, bytes(target), 1)]
    else:
        assert calls == [(bytes(source), bytes(target), 4)]
    assert source.is_dir()
    assert not target.exists()


@pytest.mark.parametrize('failure', ['library', 'symbol'])
def test_unavailable_native_function_fails_explicitly(monkeypatch, failure):
    def library(*args, **kwargs):
        if failure == 'library':
            raise OSError('libc unavailable')
        return SimpleNamespace()

    monkeypatch.setattr(publication.ctypes, 'CDLL', library)
    with pytest.raises(OSError) as error:
        publication._rename_function('renamex_np', [])
    assert error.value.errno == errno.ENOTSUP
    assert error.value.__cause__ is not None


def test_unsupported_platform_leaves_staging_and_destination_unpublished(tmp_path, monkeypatch):
    result = ch.generate(recipe())
    monkeypatch.setattr(publication.sys, 'platform', 'unsupported')
    monkeypatch.setattr(publication.os, 'rename', lambda *args: pytest.fail('unsafe fallback'))
    with pytest.raises(ch.ChancesError) as error:
        result.write(tmp_path / 'bundle')
    assert error.value.code == 'OUTPUT_FAILED'
    assert list(tmp_path.iterdir()) == []


def test_native_c_paths_reject_nul_before_calling_libc(tmp_path, monkeypatch):
    monkeypatch.setattr(publication, '_rename_function', lambda *args: pytest.fail('native call'))
    with pytest.raises(OSError) as error:
        publication.publish_directory(tmp_path / 'source', tmp_path / 'target\x00suffix')
    assert error.value.errno == errno.EINVAL


def test_windows_publication_uses_documented_exclusive_os_rename(tmp_path, monkeypatch):
    source, target = tmp_path / 'source', tmp_path / 'target'
    calls = []
    monkeypatch.setattr(publication.sys, 'platform', 'win32')
    monkeypatch.setattr(publication.os, 'rename', lambda *paths: calls.append(paths))
    monkeypatch.setattr(
        publication, '_rename_function', lambda *args: pytest.fail('POSIX native API')
    )
    publication.publish_directory(source, target)
    assert calls == [(source, target)]


@pytest.mark.parametrize('role', ['source', 'destination'])
def test_native_publication_rejects_path_subclass_callbacks(tmp_path, monkeypatch, role):
    callbacks = []

    class CallbackPath(type(tmp_path)):
        def __fspath__(self):
            callbacks.append('path')
            return super().__fspath__()

    source, destination = tmp_path / 'source', tmp_path / 'target'
    if role == 'source':
        source = CallbackPath(source)
    else:
        destination = CallbackPath(destination)
    monkeypatch.setattr(publication, '_rename_function', lambda *args: pytest.fail('native call'))
    with pytest.raises(OSError) as error:
        publication.publish_directory(source, destination)
    assert error.value.errno == errno.EINVAL
    assert callbacks == []


@pytest.mark.parametrize('action', ['write', 'generate', 'replay_output'])
@pytest.mark.parametrize('path_form', ['string', 'path'])
def test_output_nul_rejected_before_publication_preserving_prefix_content(
    tmp_path, monkeypatch, action, path_form
):
    result = ch.generate(recipe())
    source = tmp_path / 'source-bundle'
    result.write(source)
    existing = tmp_path / 'existing'
    existing.write_bytes(b'preserve')
    path = str(existing) + '\x00suffix'
    if path_form == 'path':
        path = type(tmp_path)(path)
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    monkeypatch.setattr(api, 'publish_directory', lambda *args: pytest.fail('native publication'))
    with pytest.raises(ch.ChancesError) as error:
        if action == 'write':
            result.write(path)
        elif action == 'generate':
            ch.generate(recipe(), output=path)
        else:
            ch.replay(source, output=path)
    assert error.value.code == 'OUTPUT_FAILED'
    assert existing.read_bytes() == b'preserve'
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before
    assert set(tmp_path.iterdir()) == {source, existing}


@pytest.mark.parametrize('action', ['verify', 'replay'])
@pytest.mark.parametrize('path_form', ['string', 'path'])
def test_bundle_nul_rejected_before_reading_the_prefix_bundle(tmp_path, action, path_form):
    source = tmp_path / 'source-bundle'
    ch.generate(recipe(), output=source)
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    path = str(source) + '\x00suffix'
    if path_form == 'path':
        path = type(tmp_path)(path)
    with pytest.raises(ch.ChancesError) as error:
        getattr(ch, action)(path)
    assert error.value.code == 'INVALID_BUNDLE'
    assert {p.name: p.read_bytes() for p in source.iterdir()} == before
    assert list(tmp_path.iterdir()) == [source]


_CRASH_WRITER = """
import os,sys
from pathlib import Path
import chances
import chances._api as api

def crash(stage):
    Path(sys.argv[2]).write_text(str(stage))
    os._exit(73)

api.verify = crash
chances.generate({"operation":"normal","parameters":{"size":4},"randomness":{"seed":42}}, output=Path(sys.argv[1]))
"""

_CONCURRENT_WRITER = """
import json,sys,time
from pathlib import Path
import chances
import chances._api as api

seed = int(sys.argv[2])
destination = Path(sys.argv[1])
release = destination.parent / "release"
original = api.publish_directory

def synchronized(stage,target):
    (destination.parent / (str(seed) + ".ready")).write_text(str(stage))
    deadline = time.monotonic() + 10
    while not release.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("publisher barrier timed out")
        time.sleep(0.01)
    original(stage,target)

api.publish_directory = synchronized
try:
    chances.generate({"operation":"normal","parameters":{"loc":float(seed),"scale":0,"size":4},"randomness":{"seed":seed}}, output=destination)
except chances.ChancesError as error:
    print(json.dumps({"seed":seed,"code":error.code}))
    sys.exit(2)
print(json.dumps({"seed":seed,"code":"published"}))
"""


def test_hard_crash_during_staging_cannot_reserve_destination(tmp_path):
    destination = tmp_path / 'after-crash'
    marker = tmp_path / 'crashed-stage'
    env = {**os.environ, 'PYTHONPATH': str(Path(ch.__file__).parent.parent)}
    crashed = subprocess.run(
        [sys.executable, '-c', _CRASH_WRITER, str(destination), str(marker)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert crashed.returncode == 73, crashed.stdout + crashed.stderr
    assert not destination.exists()
    abandoned = Path(marker.read_text())
    assert abandoned.parent == tmp_path and abandoned.name.startswith('.chances-')
    original = {p.name: p.read_bytes() for p in abandoned.iterdir()}
    assert set(original) == {'data.npy', 'recipe.json', 'receipt.json'}
    assert list(tmp_path.glob('*.chances-lock')) == []
    result = ch.generate(recipe(), output=destination)
    np.testing.assert_array_equal(ch.verify(destination).data, result.data)
    np.testing.assert_array_equal(ch.replay(destination).data, result.data)
    assert {p.name: p.read_bytes() for p in abandoned.iterdir()} == original
    assert list(tmp_path.glob('.chances-*')) == [abandoned]


def test_concurrent_processes_publish_one_complete_immutable_winner(tmp_path):
    destination = tmp_path / 'concurrent'
    env = {**os.environ, 'PYTHONPATH': str(Path(ch.__file__).parent.parent)}
    with (
        subprocess.Popen(
            [sys.executable, '-c', _CONCURRENT_WRITER, str(destination), '1'],
            cwd=tmp_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as first,
        subprocess.Popen(
            [sys.executable, '-c', _CONCURRENT_WRITER, str(destination), '2'],
            cwd=tmp_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ) as second,
    ):
        deadline = time.monotonic() + 15
        ready = [tmp_path / '1.ready', tmp_path / '2.ready']
        while not all(p.exists() for p in ready) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert all(p.exists() for p in ready), 'Both writers must finish unique staging.'
        stages = [Path(p.read_text()) for p in ready]
        assert len(set(stages)) == 2
        assert all(p.parent == tmp_path and p.name.startswith('.chances-') for p in stages)
        (tmp_path / 'release').write_text('publish')
        outputs = [first.communicate(timeout=15), second.communicate(timeout=15)]
        assert sorted([first.returncode, second.returncode]) == [0, 2], outputs
    outcomes = [json.loads(stdout) for stdout, _ in outputs]
    assert sorted(item['code'] for item in outcomes) == ['OUTPUT_EXISTS', 'published']
    winner = next(item['seed'] for item in outcomes if item['code'] == 'published')
    saved = ch.verify(destination)
    assert saved.receipt['spec']['randomness']['seed'] == winner
    np.testing.assert_array_equal(saved.data, np.full(4, float(winner)))
    before = {p.name: p.read_bytes() for p in destination.iterdir()}
    assert set(before) == {'data.npy', 'recipe.json', 'receipt.json'}
    with pytest.raises(ch.ChancesError) as error:
        ch.generate(recipe(), output=destination)
    assert error.value.code == 'OUTPUT_EXISTS'
    assert {p.name: p.read_bytes() for p in destination.iterdir()} == before
    assert list(tmp_path.glob('.chances-*')) == []
    assert list(tmp_path.glob('*.chances-lock')) == []
