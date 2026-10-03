"""Scientific randomness from explicit, replayable protocols."""

__version__ = '2.0.7'

from ._api import Generated, generate, inspect, replay, verify
from ._errors import ChancesError

# Legacy names import no network clients and never initialize global RNG state.
from .legacy import Randomizer, generate_random_alpha


def catalog() -> dict:
    """Return the same machine-readable operation contracts shipped to agents."""
    from ._operations import catalog as operation_catalog

    return operation_catalog()


__all__ = [
    'ChancesError',
    'Generated',
    'Randomizer',
    'catalog',
    'generate',
    'generate_random_alpha',
    'inspect',
    'replay',
    'verify',
]
