"""Fuzz protocol parsing and rehashed receipt validation with bounded fixtures."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import atheris

with atheris.instrument_imports(include=['chances']):
    import chances
    from chances._api import _read_json

LIMITS = {'max_values': 64, 'max_bytes': 4096, 'max_work': 4096}
RECIPE = {
    'operation': 'normal',
    'parameters': {'size': 8},
    'randomness': {'seed': 42, 'stream': 'fuzz/receipt'},
    'limits': LIMITS,
}
RECEIPT_PATHS = (
    ('receipt_version',),
    ('versions',),
    ('environment',),
    ('spec',),
    ('spec_sha256',),
    ('source',),
    ('randomness',),
    ('checks',),
    ('contract',),
    ('output',),
    ('checks', 'finite'),
    ('checks', 'declared_support'),
    ('contract', 'shape'),
    ('output', 'shape'),
    ('output', 'sha256'),
    ('randomness', 'seed'),
    ('randomness', 'stream'),
    ('randomness', 'engine'),
    ('randomness', 'state_before'),
    ('randomness', 'state_after'),
)


def canonical(value: object) -> bytes:
    """Hash receipt fixtures independently of the package serializer."""
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')
    ).encode('utf-8')


class ProtocolFuzzer:
    """Reuse one tiny bundle while rejecting only declared protocol errors."""

    def __init__(self, workspace: Path, evidence: Path) -> None:
        self.evidence = evidence
        self.counts: Counter[str] = Counter()
        self.input = workspace / 'protocol.json'
        self.bundle = workspace / 'bundle'
        generated = chances.generate(RECIPE, output=self.bundle)
        self.output = generated.data.tobytes()
        self.receipt = canonical(generated.receipt)
        self.recipe = canonical(generated.receipt['spec'])

    @atheris.instrument_func
    def protocol(self, payload: bytes) -> None:
        self.input.write_bytes(payload)
        value = _read_json(self.input)
        if type(value) is dict:
            # The harness declares a bounded protocol; untrusted limits cannot expand it.
            value['limits'] = dict(LIMITS)
        report = chances.inspect(value)
        assert chances.inspect(report['resolved_spec']) == report

    @atheris.instrument_func
    def structured(self, payload: bytes) -> None:
        provider = atheris.FuzzedDataProvider(payload)
        operation = provider.PickValueInList(['normal', 'uniform', 'integers'])
        regenerate = provider.ConsumeBool()
        size = provider.ConsumeIntInRange(-2, 66)
        bound = provider.ConsumeIntInRange(-2, 3)
        parameters = {'size': size}
        if operation == 'normal':
            parameters['scale'] = bound
        else:
            parameters.update({'low': 0, 'high': bound})
        spec = {
            'operation': operation,
            'parameters': parameters,
            'randomness': {
                'seed': provider.ConsumeIntInRange(-2, 2**16),
                'engine': provider.PickValueInList(['pcg64dxsm', 'philox', 'unknown']),
                'stream': provider.ConsumeUnicodeNoSurrogates(64),
            },
            'limits': dict(LIMITS),
        }
        report = chances.inspect(spec)
        assert chances.inspect(report['resolved_spec']) == report
        if regenerate:
            first = chances.generate(report['resolved_spec'])
            second = chances.generate(report['resolved_spec'])
            assert first.data.tobytes() == second.data.tobytes()
            assert first.receipt == second.receipt
            self.counts['deterministic_generation'] += 1

    @atheris.instrument_func
    def rehashed_receipt(self, payload: bytes) -> None:
        provider = atheris.FuzzedDataProvider(payload)
        receipt = json.loads(self.receipt)
        path = provider.PickValueInList(list(RECEIPT_PATHS))
        target = receipt
        for key in path[:-1]:
            target = target[key]
        number = provider.ConsumeIntInRange(-65, 65)
        text = provider.ConsumeUnicodeNoSurrogates(48)
        replacement = provider.PickValueInList(
            [None, False, True, number, number / 8, text, [], [number], {}, {'value': text}]
        )
        if provider.ConsumeBool():
            target.pop(path[-1], None)
        else:
            target[path[-1]] = replacement
        # Recompute the outer digest so mutations reach semantic receipt validators.
        contents = {key: value for key, value in receipt.items() if key != 'receipt_sha256'}
        receipt['receipt_sha256'] = hashlib.sha256(canonical(contents)).hexdigest()
        (self.bundle / 'receipt.json').write_bytes(canonical(receipt))
        assert chances.verify(self.bundle).data.tobytes() == self.output

    @atheris.instrument_func
    def raw_receipt(self, payload: bytes) -> None:
        (self.bundle / 'receipt.json').write_bytes(payload)
        assert chances.verify(self.bundle).data.tobytes() == self.output

    @atheris.instrument_func
    def run(self, data: bytes) -> None:
        if len(data) > 4096:
            raise ValueError('The fuzz campaign requires -max_len=4096.')
        mode = data[:1]
        payload = data[1:] if mode in (b'P', b'S', b'R', b'B') else data
        targets = {
            b'P': self.protocol,
            b'S': self.structured,
            b'R': self.rehashed_receipt,
            b'B': self.raw_receipt,
        }
        name = {b'P': 'protocol', b'S': 'structured', b'R': 'rehashed_receipt', b'B': 'raw_receipt'}
        target = targets.get(mode, self.protocol)
        label = name.get(mode, 'protocol')
        (self.bundle / 'recipe.json').write_bytes(self.recipe)
        try:
            target(payload)
        except chances.ChancesError as error:
            assert error.code and isinstance(error.details, dict)
            self.counts[f'{label}:rejected:{error.code}'] += 1
        else:
            self.counts[f'{label}:accepted'] += 1

    def report(self) -> None:
        """Preserve campaign outcomes alongside libFuzzer crash artifacts."""
        self.evidence.write_text(
            json.dumps(
                {'counts': dict(sorted(self.counts.items())), 'max_input_bytes': 4096}, indent=2
            )
            + '\n',
            encoding='utf-8',
        )


def main() -> None:
    """Run a fixed-seed, finite libFuzzer campaign selected by the caller."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    arguments, fuzzer_arguments = parser.parse_known_args()
    arguments.evidence.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='chances-fuzz-') as directory:
        with atheris.instrument_imports(include=['chances']):
            target = ProtocolFuzzer(Path(directory), arguments.evidence)
        atexit.register(target.report)
        atheris.Setup([sys.argv[0], *fuzzer_arguments], target.run)
        atheris.Fuzz()


if __name__ == '__main__':
    main()
