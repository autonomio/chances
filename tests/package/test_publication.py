"""Native publication cannot replace a racing destination or expose partial output."""

import ctypes
import errno
import json
import sys
from types import SimpleNamespace

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
