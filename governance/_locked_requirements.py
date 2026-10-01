"""Parse compiled dependency sets without overlooking unpinned or local entries."""
from __future__ import annotations

import re

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name

_HASH = re.compile(r'(?<!\S)--hash=sha256:[0-9a-f]{64}(?=\s|$)')


def locked_requirements(text: str) -> dict[str, Requirement]:
    """Require every active logical line to be exactly pinned and SHA256 hashed."""
    entries: dict[str, Requirement] = {}
    parts: list[str] = []
    for number, line in enumerate(text.splitlines(), 1):
        active = line.split('#', 1)[0].strip()
        if not active:
            continue
        continued = active.endswith('\\')
        parts.append(active[:-1].strip() if continued else active)
        if continued:
            continue
        block = ' '.join(parts)
        parts = []
        if not _HASH.search(block):
            raise ValueError(f'line {number}: requirement has no valid SHA256 hash')
        try:
            requirement = Requirement(_HASH.sub('', block).strip())
        except InvalidRequirement as exc:
            raise ValueError(f'line {number}: invalid compiled requirement: {exc}') from exc
        pins = list(requirement.specifier)
        if requirement.url or len(pins) != 1 or pins[0].operator != '==' or '*' in pins[0].version:
            raise ValueError(f'line {number}: require an exact index version, without URLs or paths')
        name = canonicalize_name(requirement.name)
        key = f'{name};{requirement.marker}' if requirement.marker else name
        if key in entries:
            raise ValueError(f'line {number}: duplicate compiled requirement {key}')
        entries[key] = requirement
    if parts:
        raise ValueError('unterminated requirement continuation')
    if not entries:
        raise ValueError('compiled dependency set is empty')
    return entries
