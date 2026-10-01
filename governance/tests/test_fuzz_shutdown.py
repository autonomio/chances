"""Fuzz completion releases its watchdog and cannot hide semantic receipt corruption."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import signal
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _fuzzer_module(monkeypatch, driver):
    driver.instrument_imports = lambda **kwargs: contextlib.nullcontext()
    driver.instrument_func = lambda function: function
    monkeypatch.setitem(sys.modules, 'atheris', driver)
    spec = importlib.util.spec_from_file_location('fuzz_shutdown', ROOT / 'fuzz/fuzz_protocol.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not hasattr(signal, 'setitimer'), reason='Fuzz campaigns use Unix timers.')
@pytest.mark.parametrize('status', [0, 77], ids=['completed', 'failed'])
def test_fuzzer_releases_watchdog_without_changing_exit_status(monkeypatch, tmp_path, status):
    """Exercise actual main against a native driver that leaves a real timer armed."""
    driver = ModuleType('atheris')
    events = []

    def setup(arguments, target):
        assert '-atheris_runs=10000' in arguments
        assert '-timeout=5' in arguments
        assert callable(target)
        events.append('setup')

    def finish_campaign():
        signal.setitimer(signal.ITIMER_REAL, 10, 10)
        assert signal.getitimer(signal.ITIMER_REAL)[0] > 0
        events.append('armed')
        raise SystemExit(status)

    driver.Setup = setup
    driver.Fuzz = finish_campaign
    module = _fuzzer_module(monkeypatch, driver)
    # Bundle initialization is unrelated to this native-driver shutdown regression.
    target = SimpleNamespace(run=lambda data: None, report=lambda: None)
    monkeypatch.setattr(module, 'ProtocolFuzzer', lambda *args: target)
    monkeypatch.setattr(module, 'atexit', SimpleNamespace(register=lambda callback: None))
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'fuzz_protocol.py',
            '--evidence',
            str(tmp_path / 'outcomes.json'),
            '-atheris_runs=10000',
            '-timeout=5',
        ],
    )
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    try:
        with pytest.raises(SystemExit) as failure:
            module.main()
        assert failure.value.code == status
        assert events == ['setup', 'armed']
        assert signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0)
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)


@pytest.mark.parametrize('replacement', [True, False], ids=['no-op', 'corrupt-metadata'])
def test_rehashed_receipt_target_detects_false_acceptance(monkeypatch, tmp_path, replacement):
    """An incorrect verifier returning identical arrays must still expose altered metadata."""
    driver = ModuleType('atheris')

    class Provider:
        def __init__(self, payload):
            assert payload == b'fixture'

        def PickValueInList(self, values):
            if isinstance(values[0], tuple):
                return ('checks', 'finite')
            return replacement

        def ConsumeIntInRange(self, minimum, maximum):
            return 0

        def ConsumeUnicodeNoSurrogates(self, maximum):
            return ''

        def ConsumeBool(self):
            return False

    driver.FuzzedDataProvider = Provider
    module = _fuzzer_module(monkeypatch, driver)
    target = module.ProtocolFuzzer(tmp_path, tmp_path / 'outcomes.json')
    original = module.chances.verify(target.bundle)

    def incorrectly_accept(bundle):
        receipt = json.loads((bundle / 'receipt.json').read_text())
        return SimpleNamespace(data=original.data, receipt=receipt)

    monkeypatch.setattr(module.chances, 'verify', incorrectly_accept)
    if replacement:
        target.rehashed_receipt(b'fixture')
    else:
        with pytest.raises(AssertionError):
            target.rehashed_receipt(b'fixture')
