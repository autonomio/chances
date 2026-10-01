"""Deprecated integer-index facade. New research should use receipt-bearing protocols."""

from __future__ import annotations

import math
import random
import warnings

import numpy as np

from ._errors import ChancesError
from ._random import generator, resolve_randomness


class Randomizer:
    """Compatibility names with isolated seed=0 streams and corrected validation.

    Design methods return legacy index lists and discard multidimensional geometry.
    They are not the new scientific design interface. The old output streams were
    undefined and are deliberately not reproduced by this major release.
    """

    def __init__(self, max_value: int, n: int, *, seed: int = 0) -> None:
        warnings.warn(
            'Randomizer is deprecated; use chances.generate for explicit contracts and receipts.',
            DeprecationWarning,
            stacklevel=2,
        )
        if (
            type(max_value) is not int
            or max_value < 1
            or type(n) is not int
            or not 0 <= n <= max_value
        ):
            raise ChancesError(
                'INVALID_DOMAIN', 'Use max_value >= 1 and 0 <= n <= max_value, both integers.'
            )
        if max_value > 10_000_000:
            raise ChancesError(
                'RESOURCE_LIMIT',
                'Legacy index methods are limited to ten million values; use a declared protocol.',
            )
        resolve_randomness({'seed': seed})
        self.len, self.n, self.seed = max_value, n, seed

    def _generate(
        self, operation: str, parameters: dict, *, engine: str = 'pcg64dxsm'
    ) -> np.ndarray:
        from . import generate

        return generate(
            {
                'version': 1,
                'operation': operation,
                'parameters': parameters,
                'randomness': {
                    'seed': self.seed,
                    'stream': 'legacy/' + operation,
                    'engine': engine,
                },
            }
        ).data

    def uniform_mersenne(self) -> list[int]:
        return self._generate(
            'choice', {'n': self.len, 'size': self.n, 'replace': False}, engine='mt19937'
        ).tolist()

    def uniform_crypto(self) -> list[int]:
        """Fresh OS-backed, uniform sampling without replacement; no seeded replay."""
        return random.SystemRandom().sample(range(self.len), self.n)

    def latin_matrix(self) -> list[int]:
        if not self.n:
            return []
        points = self._generate('latin_hypercube', {'n': self.len, 'd': 1})
        return np.floor(points[:, 0] * self.len).astype(np.int64)[: self.n].tolist()

    def latin_sudoku(self, dims: int = 2, sudoku_boxes: int = 1) -> list[int]:
        if not self.n:
            return []
        points = self._generate('sudoku', {'n': self.len, 'd': dims, 'boxes': sudoku_boxes})
        return np.floor(points[:, 0] * self.len).astype(np.int64)[: self.n].tolist()

    def latin_improved(self) -> list[int]:
        """Bounded legacy 1D greedy maximin heuristic, with an owned RNG."""
        if self.n == 0:
            return []
        candidates_count = 100
        if self.len * self.len * candidates_count > 100_000_000:
            raise ChancesError(
                'RESOURCE_LIMIT', 'The legacy maximin heuristic exceeds its quadratic work budget.'
            )
        if self.len == 1:
            return [0]
        rng = generator(resolve_randomness({'seed': self.seed, 'stream': 'legacy/latin_improved'}))
        available = rng.permutation(self.len).tolist()
        design = np.empty(self.len, dtype=np.int64)
        design[0] = available.pop()
        for i in range(1, self.len - 1):
            repeats = math.ceil(candidates_count / len(available))
            candidates = rng.permutation(np.tile(available, repeats))[:candidates_count]
            distances = np.abs(design[:i, None] - candidates)
            distances = np.minimum(distances, self.len - 1 - distances)
            point = int(candidates[np.argmax(distances.min(axis=0))])
            design[i] = point
            available.remove(point)
        design[-1] = available.pop()
        return design[: self.n].tolist()

    def sobol(self) -> list[int]:
        if not self.n:
            return []
        return self._match_index(
            self._generate('sobol', {'n': self.len, 'd': 1, 'scramble': False})[:, 0]
        )[: self.n]

    def halton(self) -> list[int]:
        if not self.n:
            return []
        return self._match_index(
            self._generate('halton', {'n': self.len, 'd': 1, 'scramble': False})[:, 0]
        )[: self.n]

    def korobov_matrix(self) -> list[int]:
        if not self.n:
            return []
        points = self._generate('korobov', {'n': self.len, 'd': 2})
        return np.floor(points[:, 1] * self.len).astype(np.int64)[: self.n].tolist()

    def ambience(self) -> None:
        raise ChancesError(
            'ENTROPY_PROVIDER_UNAVAILABLE',
            'The bundled RANDOM.ORG integration was removed; provide independently acquired data to the declared protocol.',
        )

    def quantum(self) -> None:
        raise ChancesError(
            'ENTROPY_PROVIDER_UNAVAILABLE',
            'The unsafe bundled quantum integration was removed; archive independently acquired entropy before use.',
        )

    def _match_index(self, values: np.ndarray) -> list[int]:
        return np.argsort(values, kind='stable').astype(np.int64).tolist()


def generate_random_alpha(
    n: int = 1, dtype: type[str] | type[list] = str, *, seed: int = 0
) -> str | list[str]:
    """Deprecated deterministic alphabet utility; never consumes global RNG state."""
    warnings.warn(
        'generate_random_alpha is deprecated; use choice with a string source.',
        DeprecationWarning,
        stacklevel=2,
    )
    if type(n) is not int or not 0 <= n <= 10_000_000 or dtype not in (str, list):
        raise ChancesError('INVALID_DOMAIN', 'Use 0 <= n <= 10000000 and dtype str or list.')
    rng = generator(resolve_randomness({'seed': seed, 'stream': 'legacy/alphabet'}))
    values = np.asarray(list('abcdefghijklmnopqrstuvwxyz'))[rng.integers(0, 26, size=n)].tolist()
    return ''.join(values) if dtype is str else values
