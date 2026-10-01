"""A completed fuzz campaign must release its native watchdog before shutdown."""

from __future__ import annotations

import contextlib
import importlib.util
import signal
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not hasattr(signal, 'setitimer'), reason='Fuzz campaigns use Unix timers.')
@pytest.mark.parametrize('status', [0, 77], ids=['completed', 'failed'])
def test_fuzzer_releases_watchdog_without_changing_exit_status(monkeypatch, tmp_path, status):
    """Exercise actual main against a native-driver fixture that leaves a real timer armed."""
    driver = ModuleType('atheris')
    driver.instrument_imports = lambda **kwargs: contextlib.nullcontext()
    driver.instrument_func = lambda function: function
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
    monkeypatch.setitem(sys.modules, 'atheris', driver)
    spec = importlib.util.spec_from_file_location('fuzz_shutdown', ROOT / 'fuzz/fuzz_protocol.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Initialization is unrelated to this shutdown regression; Atheris execution is a fixture.
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
