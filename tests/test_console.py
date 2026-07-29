"""Console output must survive a terminal that cannot encode what we print.

Windows consoles default to cp1252 or cp437, and both reject most of the icon
set. CI caught it the only way it can be caught -- running a real command on a
real Windows runner, where ``coderrr doctor`` died on the info icon.

``sys.stdout`` is patched inside each test body rather than from a fixture:
pytest's capture manager reassigns ``sys.stdout`` between the setup and call
phases, so a patch applied during setup is silently undone before the test runs.
"""

from __future__ import annotations

import io
import sys

import pytest

from coderrr.ui.console import _ASCII_ICONS, _ICONS, Console


def _fake_stdout(
    monkeypatch: pytest.MonkeyPatch, encoding: str
) -> tuple[io.BytesIO, io.TextIOWrapper]:
    """Point ``sys.stdout`` at a stream with ``encoding`` and strict errors."""
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding=encoding, errors="strict")
    monkeypatch.setattr(sys, "stdout", stream)
    return raw, stream


def test_unicode_icons_on_a_utf8_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_stdout(monkeypatch, "utf-8")
    assert Console()._icons is _ICONS


@pytest.mark.parametrize("encoding", ["cp1252", "cp437", "ascii"])
def test_ascii_icons_when_the_terminal_cannot_encode_them(
    monkeypatch: pytest.MonkeyPatch, encoding: str
) -> None:
    _fake_stdout(monkeypatch, encoding)
    assert Console()._icons is _ASCII_ICONS


def test_ascii_icons_are_encodable_everywhere() -> None:
    for encoding in ("cp1252", "cp437", "ascii"):
        "".join(_ASCII_ICONS.values()).encode(encoding)


def test_icon_tables_cover_the_same_keys() -> None:
    assert _ICONS.keys() == _ASCII_ICONS.keys()


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


def test_quiet_console_still_selects_icons(monkeypatch: pytest.MonkeyPatch) -> None:
    """QuietConsole runs the same __init__; it must not crash on a legacy stream."""
    from coderrr.ui.console import QuietConsole

    _fake_stdout(monkeypatch, "cp1252")
    assert QuietConsole()._icons is _ASCII_ICONS
