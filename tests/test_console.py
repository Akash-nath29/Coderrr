"""Console output must survive a terminal that cannot encode what we print.

Windows consoles default to cp1252 or cp437, and both reject most of the icon
set. CI caught it the only way it can be caught -- running a real command on a
real Windows runner, where ``coderrr doctor`` died on the info icon.

Two rules apply here, learned from getting them wrong:

* Assert on ``_encodable`` and ``_icons_for`` rather than on a ``Console``
  built for the host. Icon choice depends on ``legacy_windows``, so a test that
  goes through ``Console()`` asserts something different on a Windows runner
  than it does on Linux. Only properties true on every platform belong in the
  integration tests below.
* Patch ``sys.stdout`` inside the test body, never from a fixture. pytest's
  capture manager reassigns it between the setup and call phases, so a patch
  applied during setup is silently undone before the test runs.
"""

from __future__ import annotations

import io
import sys
from typing import IO, cast

import pytest

from coderrr.ui.console import (
    _ASCII_ICONS,
    _ICONS,
    Console,
    QuietConsole,
    _encodable,
    _icons_for,
)


def _fake_stdout(
    monkeypatch: pytest.MonkeyPatch, encoding: str
) -> tuple[io.BytesIO, io.TextIOWrapper]:
    """Point ``sys.stdout`` at a stream with ``encoding`` and strict errors."""
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding=encoding, errors="strict")
    monkeypatch.setattr(sys, "stdout", stream)
    return raw, stream


# -- the decision, isolated from the host --------------------------------------


@pytest.mark.parametrize(
    ("encodable", "legacy_windows", "expected"),
    [
        (True, False, _ICONS),
        (True, True, _ASCII_ICONS),  # a legacy console that could encode anyway
        (False, False, _ASCII_ICONS),
        (False, True, _ASCII_ICONS),
    ],
)
def test_icon_choice(encodable: bool, legacy_windows: bool, expected: dict[str, str]) -> None:
    assert _icons_for(encodable=encodable, legacy_windows=legacy_windows) is expected


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [("utf-8", True), ("cp1252", False), ("cp437", False), ("ascii", False)],
)
def test_encodable_follows_the_stream_encoding(encoding: str, expected: bool) -> None:
    stream = io.TextIOWrapper(io.BytesIO(), encoding=encoding)
    assert _encodable("".join(_ICONS.values()), stream) is expected


def test_encodable_allows_a_stream_with_no_encoding() -> None:
    """An in-memory buffer never runs the encode step, so nothing can fail."""
    assert _encodable("◇", cast(IO[str], io.StringIO())) is True


def test_encodable_rejects_an_unknown_codec() -> None:
    class Stub:
        encoding = "definitely-not-a-codec"

    assert _encodable("◇", cast(IO[str], Stub())) is False


def test_ascii_icons_are_encodable_everywhere() -> None:
    for encoding in ("cp1252", "cp437", "ascii"):
        "".join(_ASCII_ICONS.values()).encode(encoding)


def test_icon_tables_cover_the_same_keys() -> None:
    assert _ICONS.keys() == _ASCII_ICONS.keys()


# -- integration: properties that hold on every platform -----------------------


def test_a_stream_that_cannot_encode_gets_ascii_icons(monkeypatch: pytest.MonkeyPatch) -> None:
    """False for `encodable` forces ASCII regardless of the host platform."""
    _fake_stdout(monkeypatch, "cp1252")
    assert Console()._icons is _ASCII_ICONS


def test_quiet_console_selects_icons_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """QuietConsole runs the same __init__; it must not crash on a legacy stream."""
    _fake_stdout(monkeypatch, "cp1252")
    assert QuietConsole()._icons is _ASCII_ICONS


def test_chrome_prints_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    raw, stream = _fake_stdout(monkeypatch, "cp1252")
    ui = Console(interactive=False)

    ui.info("info")
    ui.success("success")
    ui.warning("warning")
    ui.error("error")
    ui.tool_call("read_file", "src/coderrr/cli.py")
    ui.tool_result("read_file", True, "42 lines")
    ui.tool_result("read_file", False)

    stream.flush()
    assert raw.getvalue(), "nothing reached the stream"


def test_table_cells_are_not_read_as_markup(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bracketed text in a cell is data and must survive to the screen.

    Rich reads ``[...]`` as a style tag, so an MCP server on an IPv6 address, or
    a spec titled "Add [beta] support", used to lose the bracketed part with no
    error anywhere.
    """
    raw, stream = _fake_stdout(monkeypatch, "utf-8")
    ui = Console(interactive=False)

    ui.table(
        ["Server", "Target"],
        [["v6", "http://[::1]:3845/mcp"], ["spec", "Add [beta] support"]],
    )

    stream.flush()
    written = raw.getvalue().decode("utf-8")
    assert "[::1]" in written
    assert "[beta]" in written


def test_model_generated_text_degrades_instead_of_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unencodable model output must not raise -- we cannot enumerate it.

    A spec containing an arrow or a box-drawing character is ordinary output.
    Printing one used to take the whole command down partway through.
    """
    raw, stream = _fake_stdout(monkeypatch, "cp1252")
    ui = Console(interactive=False)

    ui.markdown("## Data Flow\n\nRequest → API ─▶ worker\n")
    ui.info("sandbox: scratch — no isolation")

    stream.flush()
    written = raw.getvalue()
    assert written, "nothing reached the stream"
    assert b"?" in written, "unencodable characters should be replaced, not dropped"


def test_a_utf8_stream_is_not_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing is substituted when the stream can carry it, legacy host or not."""
    raw, stream = _fake_stdout(monkeypatch, "utf-8")
    ui = Console(interactive=False)

    ui.info("sandbox: scratch — no isolation")

    stream.flush()
    assert "—".encode() in raw.getvalue()
