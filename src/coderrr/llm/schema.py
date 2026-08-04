"""JSON Schema normalization for tool payloads.

Tool schemas reach providers from two places: pydantic models, which emit tidy
inline objects, and MCP servers, which emit whatever their author wrote --
commonly ``$ref`` pointers into a ``$defs`` section, and occasionally recursive
ones.

Providers do not agree on how much of JSON Schema they accept, and none of them
resolve ``$ref``. Inlining references here means each adapter only has to decide
which *keywords* it supports, never how to chase a pointer.
"""

from __future__ import annotations

from typing import Any

#: Reference sections, inlined and then dropped.
_DEF_SECTIONS = ("$defs", "definitions")

#: Meaningless to a provider once references are resolved.
_DROP_KEYS = frozenset({"$schema", "$id", "$comment", "$defs", "definitions"})

#: Depth ceiling. A schema nested deeper than this is pathological, and the
#: cutoff also bounds the blowup from inlining a definition reused many times.
MAX_DEPTH = 16


def flatten_refs(schema: Any) -> dict[str, Any]:
    """Inline ``$ref`` pointers and guarantee an object root.

    A reference that cannot be resolved, or that closes a cycle, degrades to an
    unconstrained object rather than raising: a server whose schema we cannot
    fully model is still usable, because the server itself does the real
    validation. Refusing the tool outright would be a worse trade.
    """
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}

    definitions: dict[str, Any] = {}
    for section in _DEF_SECTIONS:
        found = schema.get(section)
        if isinstance(found, dict):
            definitions.update(found)

    resolved = _walk(schema, definitions, (), 0)
    if not isinstance(resolved, dict):
        return {"type": "object", "properties": {}}

    # Providers require an object at the root of a tool's parameters.
    if resolved.get("type") != "object":
        resolved["type"] = "object"
    if not isinstance(resolved.get("properties"), dict):
        resolved["properties"] = {}
    return resolved


def _walk(node: Any, definitions: dict[str, Any], stack: tuple[str, ...], depth: int) -> Any:
    if depth > MAX_DEPTH:
        return {"type": "object"}

    if isinstance(node, list):
        return [_walk(item, definitions, stack, depth + 1) for item in node]

    if not isinstance(node, dict):
        return node

    ref = node.get("$ref")
    if isinstance(ref, str):
        return _resolve(ref, node, definitions, stack, depth)

    return {
        key: _walk(value, definitions, stack, depth + 1)
        for key, value in node.items()
        if key not in _DROP_KEYS
    }


def _resolve(
    ref: str,
    node: dict[str, Any],
    definitions: dict[str, Any],
    stack: tuple[str, ...],
    depth: int,
) -> dict[str, Any]:
    """Inline one ``$ref``, layering the node's own keywords on top.

    Keywords sitting beside a ``$ref`` (typically ``description``) are kept and
    win over the target's, which is what a reader expects from
    ``{"$ref": ..., "description": "the specific one"}``.
    """
    siblings = {
        key: _walk(value, definitions, stack, depth + 1)
        for key, value in node.items()
        if key != "$ref" and key not in _DROP_KEYS
    }

    name = _ref_name(ref)
    # A self-reference, an unresolvable pointer, or a cycle. Recursive schemas
    # are legal and not rare (a tree of design nodes, a threaded comment), so
    # this path is expected rather than exceptional.
    if name is None or name in stack or name not in definitions:
        return {"type": "object", **siblings}

    target = _walk(definitions[name], definitions, (*stack, name), depth + 1)
    if not isinstance(target, dict):
        return {"type": "object", **siblings}
    return {**target, **siblings}


def _ref_name(ref: str) -> str | None:
    """Last segment of a local ``#/$defs/Name`` pointer, if that is what it is.

    External references -- another file, an ``http://`` URL -- are deliberately
    not fetched, so they resolve to nothing and degrade like a cycle.
    """
    if not ref.startswith("#/"):
        return None
    segments = [segment for segment in ref[2:].split("/") if segment]
    if len(segments) < 2 or segments[0] not in _DEF_SECTIONS:
        return None
    return segments[-1]
