"""Stable, machine-readable failures; no statistical fallback."""

from __future__ import annotations


class ChancesError(ValueError):
    """An operation could not satisfy the declared scientific contract."""

    def __init__(self, code: str, message: str, details: dict[str, object] | None = None) -> None:
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, object]:
        return {'code': self.code, 'message': str(self), 'details': self.details}
