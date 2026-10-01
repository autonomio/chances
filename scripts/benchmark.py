#!/usr/bin/env python3
"""Measure bulk generation with checks/receipts against the identical NumPy engine."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    import numpy as np

    import chances
    from chances._random import generator, resolve_randomness

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--values', type=int, default=1_000_000)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.values < 1 or not 1 <= args.repeats <= 100:
        parser.error('values must be positive; repeats must be 1..100')
    randomness = resolve_randomness({'seed': 42, 'stream': 'benchmark/normal'})
    recipe = {'operation': 'normal', 'parameters': {'size': args.values}, 'randomness': randomness}
    chances.inspect(recipe)
    chances.generate(recipe)  # Import/warm-up costs do not dominate repeated bulk draws.
    complete, bare = [], []
    for _ in range(args.repeats):
        start = time.perf_counter()
        result = chances.generate(recipe)
        complete.append(time.perf_counter() - start)
        start = time.perf_counter()
        native = generator(randomness).normal(0, 1, size=args.values)
        bare.append(time.perf_counter() - start)
        assert result.data.shape == native.shape
        assert np.array_equal(result.data, native)
    seconds = statistics.median(complete)
    report = {
        'versions': result.receipt['versions'],
        'environment': result.receipt['environment'],
        'operation': 'normal',
        'values': args.values,
        'repeats': args.repeats,
        'generation_with_checks_and_receipt_median_seconds': seconds,
        'bare_engine_median_seconds': statistics.median(bare),
        'values_per_second': args.values / seconds,
        'receipt_bytes': len(json.dumps(result.receipt, sort_keys=True).encode()),
        'scope': 'Warm local float64 bulk generation; publication/I/O excluded. Timings are measurements, not portable performance guarantees.',
    }
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')


if __name__ == '__main__':
    main()
