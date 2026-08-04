"""Known-server shorthands for ``coderrr mcp add``.

Empty by design. The resolution step exists now so that curated servers can be
added later without changing the command's shape: ``coderrr mcp add figma``
already routes through here before its argument is treated as a URL or a
command, so populating :data:`BUILTIN` is the whole of that future change.

Nothing here is fetched from the network. A catalog that resolved names against a
remote index would let whoever controls the index decide what command runs on the
user's machine, which is not a trade worth making for saved typing.
"""

from __future__ import annotations

from coderrr.config import McpServerConfig

#: Shorthand name -> ready-made configuration.
BUILTIN: dict[str, McpServerConfig] = {}


def resolve(name: str) -> McpServerConfig | None:
    """The built-in configuration for ``name``, if there is one."""
    known = BUILTIN.get(name.strip().lower())
    return known.model_copy(deep=True) if known is not None else None


def names() -> list[str]:
    return sorted(BUILTIN)
