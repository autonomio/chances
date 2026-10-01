"""Publish complete directories with native atomic destination exclusion."""

from __future__ import annotations

import ctypes
import errno
import os
import sys
from pathlib import Path
from typing import Protocol, cast

_ArgumentType = type[ctypes.c_int] | type[ctypes.c_uint] | type[ctypes.c_char_p]
_NATIVE_PATH = type(Path())


class _RenameFunction(Protocol):
    """The bounded C signature used only for literal native rename symbols."""

    argtypes: list[_ArgumentType]
    restype: type[ctypes.c_int]

    def __call__(self, *arguments: int | bytes) -> int: ...


def _rename_function(name: str, arguments: list[_ArgumentType]) -> _RenameFunction:
    try:
        library = ctypes.CDLL(None, use_errno=True)
        function = cast(_RenameFunction, getattr(library, name))
    except (OSError, AttributeError) as error:
        raise OSError(
            errno.ENOTSUP, 'Native atomic destination exclusion is unavailable.'
        ) from error
    function.argtypes = arguments
    function.restype = ctypes.c_int
    return function


def publish_directory(source: Path, destination: Path) -> None:
    """Rename a staged directory atomically, refusing every existing destination."""
    if type(source) is not _NATIVE_PATH or type(destination) is not _NATIVE_PATH:
        raise OSError(errno.EINVAL, 'Atomic publication requires native pathlib paths.')
    old, new = os.fsencode(source), os.fsencode(destination)
    if b'\x00' in old or b'\x00' in new:
        raise OSError(errno.EINVAL, 'Native paths cannot contain NUL bytes.')
    if sys.platform == 'win32':
        # Windows os.rename rejects an existing target, including empty directories.
        os.rename(source, destination)
        return
    if sys.platform == 'darwin':
        # macOS SDK sys/stdio.h: RENAME_EXCL = 0x00000004.
        function = _rename_function('renamex_np', [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint])
        result = function(old, new, 4)
    elif sys.platform == 'linux':
        # Linux UAPI: AT_FDCWD = -100; RENAME_NOREPLACE = 1.
        function = _rename_function(
            'renameat2',
            [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint],
        )
        result = function(-100, old, -100, new, 1)
    else:
        raise OSError(errno.ENOTSUP, 'This platform lacks supported atomic destination exclusion.')
    if result != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(destination))
