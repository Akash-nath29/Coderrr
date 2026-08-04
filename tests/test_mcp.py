"""Custom MCP server support.

Everything here runs against :class:`FakeConnection` rather than the ``mcp`` SDK.
That is the point of the layering: naming, schema handling, approval and result
rendering are all reachable without the optional dependency, a subprocess, or a
network. Only :mod:`coderrr.mcp.client` needs the real thing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from coderrr.agent.modes import AgentMode
from coderrr.config import (
    Config,
    McpConfig,
    McpServerConfig,
    expand_env_refs,
    load_config,
    save_config,
)
from coderrr.llm.schema import flatten_refs
from coderrr.llm.types import ToolClass, ToolUseBlock
from coderrr.mcp import naming
from coderrr.mcp import setup as mcp_setup
from coderrr.mcp.bridge import build_tool, render_result
from coderrr.mcp.client import _reason, _to_block, _to_definition, _unwrap
from coderrr.mcp.manager import McpManager
from coderrr.mcp.types import (
    ManagedConnection,
    McpBlock,
    McpCallResult,
    McpError,
    McpToolDef,
)
from coderrr.policy.gate import Decision, evaluate
from coderrr.tools.base import ToolContext
from coderrr.tools.registry import ALLOW_ALWAYS, ALLOW_ONCE, DENY_TOOL, ToolRegistry
from coderrr.ui import repl as repl_module
from coderrr.ui.repl import Repl
from tests.fakes import FakeProvider, RecordingConsole


class FakeConnection:
    """Stands in for a connected server."""

    def __init__(
        self,
        name: str = "figma",
        *,
        tools: list[McpToolDef] | None = None,
        result: McpCallResult | None = None,
        fail_on_open: str = "",
    ) -> None:
        self._name = name
        self._tools = tools if tools is not None else [McpToolDef(name="get_code")]
        self._result = result or McpCallResult(blocks=(McpBlock(text="ok"),))
        self._fail_on_open = fail_on_open
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.opened = False
        self.closed = False

    @property
    def server(self) -> str:
        return self._name

    async def open(self) -> None:
        if self._fail_on_open:
            raise McpError(self._fail_on_open)
        self.opened = True

    async def aclose(self) -> None:
        self.closed = True

    async def list_tools(self) -> list[McpToolDef]:
        return list(self._tools)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> McpCallResult:
        self.calls.append((name, arguments))
        if isinstance(self._result, Exception):  # pragma: no cover - defensive
            raise self._result
        return self._result


def factory_for(connection: FakeConnection):  # type: ignore[no-untyped-def]
    def build(name: str, config: McpServerConfig) -> ManagedConnection:
        return connection  # type: ignore[return-value]

    return build


def http_server(**kwargs: Any) -> McpServerConfig:
    return McpServerConfig(transport="http", url="http://127.0.0.1:3845/mcp", **kwargs)


async def manager_with(
    connection: FakeConnection, server: McpServerConfig | None = None, **kwargs: Any
) -> McpManager:
    config = McpConfig(servers={connection.server: server or http_server()})
    manager = McpManager(config=config, connection_factory=factory_for(connection), **kwargs)
    await manager.connect()
    return manager


# -- naming --------------------------------------------------------------


def test_qualified_names_carry_server_and_tool() -> None:
    assert naming.qualify("figma", "get_code") == "mcp__figma__get_code"


@pytest.mark.parametrize(
    ("server", "tool"),
    [("my.server", "get code"), ("a/b", "do:it"), ("Ünïcode", "tøol")],
)
def test_names_are_reduced_to_accepted_characters(server: str, tool: str) -> None:
    name = naming.qualify(server, tool)
    assert re_ok(name), name
    assert len(name) <= naming.MAX_NAME


def re_ok(name: str) -> bool:
    import re

    return re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name) is not None


def test_long_names_are_truncated_but_stay_distinct() -> None:
    first = naming.qualify("s" * 40, "t" * 40)
    second = naming.qualify("s" * 40, "t" * 41)
    assert len(first) <= naming.MAX_NAME
    assert first != second


def test_collisions_get_a_distinct_name() -> None:
    """Two servers can sanitize to the same string."""
    first = naming.qualify("my.server", "search")
    second = naming.qualify("my/server", "search", taken={first})
    assert first != second
    assert len(second) <= naming.MAX_NAME


def test_split_recovers_the_parts() -> None:
    assert naming.split("mcp__figma__get_code") == ("figma", "get_code")
    assert naming.split("read_file") is None


# -- schema flattening ---------------------------------------------------


def test_refs_are_inlined() -> None:
    flat = flatten_refs(
        {
            "type": "object",
            "properties": {"node": {"$ref": "#/$defs/Node"}},
            "$defs": {"Node": {"type": "string", "description": "an id"}},
        }
    )
    assert flat["properties"]["node"] == {"type": "string", "description": "an id"}
    assert "$defs" not in flat


def test_sibling_keywords_win_over_the_target() -> None:
    flat = flatten_refs(
        {
            "type": "object",
            "properties": {"node": {"$ref": "#/$defs/Node", "description": "the specific one"}},
            "$defs": {"Node": {"type": "string", "description": "generic"}},
        }
    )
    assert flat["properties"]["node"]["description"] == "the specific one"


def test_recursive_refs_terminate() -> None:
    """A tree-shaped schema is legal and must not hang or recurse forever."""
    flat = flatten_refs(
        {
            "type": "object",
            "properties": {"root": {"$ref": "#/$defs/Node"}},
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {"child": {"$ref": "#/$defs/Node"}},
                }
            },
        }
    )
    assert flat["properties"]["root"]["type"] == "object"


def test_unresolvable_and_external_refs_degrade() -> None:
    for ref in ("#/$defs/Missing", "https://example.com/schema.json", "#"):
        flat = flatten_refs({"type": "object", "properties": {"x": {"$ref": ref}}})
        assert flat["properties"]["x"]["type"] == "object"


def test_root_is_always_an_object() -> None:
    assert flatten_refs({"type": "string"})["type"] == "object"
    assert flatten_refs("nonsense")["properties"] == {}


# -- the bridged tool ----------------------------------------------------


def bridged(definition: McpToolDef, connection: FakeConnection | None = None):  # type: ignore[no-untyped-def]
    connection = connection or FakeConnection()
    return build_tool(
        connection=connection,  # type: ignore[arg-type]
        definition=definition,
        qualified_name=naming.qualify(connection.server, definition.name),
        max_result_bytes=1024,
    )


def test_bridged_tool_exports_a_usable_spec() -> None:
    tool = bridged(
        McpToolDef(
            name="get_code",
            description="Return code for a frame.",
            input_schema={"type": "object", "properties": {"id": {"type": "string"}}},
        )
    )
    spec = tool.spec()

    assert spec.name == "mcp__figma__get_code"
    assert spec.klass is ToolClass.EXTERNAL
    assert spec.input_schema["type"] == "object"
    # The server is named so the model can choose between similar tools.
    assert "figma" in spec.description
    assert "Return code for a frame." in spec.description


def test_bridged_tool_keeps_the_real_server_and_tool_name() -> None:
    tool = bridged(McpToolDef(name="get_code"))
    assert tool.server == "figma"
    assert tool.tool_name == "get_code"


def test_missing_required_arguments_are_caught_locally() -> None:
    tool = bridged(
        McpToolDef(
            name="get_code",
            input_schema={"type": "object", "required": ["id"], "properties": {}},
        )
    )
    with pytest.raises(ValueError, match="id"):
        tool.validate_input({})
    assert tool.validate_input({"id": "1"}) == {"id": "1"}


def test_unknown_arguments_are_passed_through() -> None:
    """The server owns its schema; we do not second-guess it."""
    tool = bridged(McpToolDef(name="get_code"))
    assert tool.validate_input({"whatever": 1}) == {"whatever": 1}


async def test_running_a_bridged_tool_calls_the_server(ctx: ToolContext) -> None:
    connection = FakeConnection()
    tool = bridged(McpToolDef(name="get_code"), connection)

    result = await tool.run({"id": "7"}, ctx)

    assert connection.calls == [("get_code", {"id": "7"})]
    assert not result.is_error
    assert "ok" in result.content


async def test_transport_failure_becomes_a_tool_error(ctx: ToolContext) -> None:
    class Broken(FakeConnection):
        async def call_tool(self, name: str, arguments: dict[str, Any]) -> McpCallResult:
            raise McpError("connection reset")

    tool = bridged(McpToolDef(name="get_code"), Broken())
    result = await tool.run({}, ctx)

    assert result.is_error
    assert "connection reset" in result.content


async def test_server_reported_error_reaches_the_model(ctx: ToolContext) -> None:
    """A tool-level failure is information to correct, not a crash."""
    connection = FakeConnection(
        result=McpCallResult(blocks=(McpBlock(text="no such frame"),), is_error=True)
    )
    tool = bridged(McpToolDef(name="get_code"), connection)

    result = await tool.run({}, ctx)

    assert result.is_error
    assert "no such frame" in result.content


# -- result rendering ----------------------------------------------------


def test_results_are_marked_as_external_data() -> None:
    content, _ = render_result(
        McpCallResult(blocks=(McpBlock(text="hello"),)), server="figma", limit=1024
    )
    assert "figma" in content
    assert "not instructions" in content
    assert "hello" in content


def test_binary_blocks_are_reported_not_inlined() -> None:
    content, _ = render_result(
        McpCallResult(blocks=(McpBlock(kind="image", mime="image/png"),)),
        server="figma",
        limit=1024,
    )
    assert "image/png" in content
    assert "omitted" in content


def test_structured_content_is_used_when_there_is_no_text() -> None:
    content, _ = render_result(McpCallResult(structured={"count": 2}), server="linear", limit=1024)
    assert '"count": 2' in content


def test_oversized_results_are_truncated() -> None:
    content, display = render_result(
        McpCallResult(blocks=(McpBlock(text="x" * 5000),)), server="figma", limit=500
    )
    assert len(content.encode("utf-8")) < 1200
    assert "truncated" in content
    assert "truncated" in display


def test_empty_results_say_so() -> None:
    content, _ = render_result(McpCallResult(), server="figma", limit=1024)
    assert content == ""


# -- the gate ------------------------------------------------------------


def test_external_tools_exist_in_planning_mode() -> None:
    """Reading external context is most useful while the plan is being written."""
    gate = evaluate(klass=ToolClass.EXTERNAL, mode=AgentMode.PLANNING)
    assert gate.decision is Decision.ASK


def test_write_tools_are_still_absent_from_planning() -> None:
    """The invariant EXTERNAL must not have weakened."""
    gate = evaluate(klass=ToolClass.WRITE, mode=AgentMode.PLANNING)
    assert gate.decision is Decision.DENY


def test_external_tools_ask_by_default() -> None:
    for mode in (AgentMode.PLANNING, AgentMode.EXECUTION):
        assert evaluate(klass=ToolClass.EXTERNAL, mode=mode).decision is Decision.ASK


def test_remembered_approval_stops_the_asking() -> None:
    gate = evaluate(klass=ToolClass.EXTERNAL, mode=AgentMode.EXECUTION, preapproved=True)
    assert gate.decision is Decision.ALLOW


def test_denied_tools_are_refused_outright() -> None:
    gate = evaluate(klass=ToolClass.EXTERNAL, mode=AgentMode.EXECUTION, denied=True)
    assert gate.decision is Decision.DENY


def test_deny_beats_allow_when_both_are_set() -> None:
    gate = evaluate(
        klass=ToolClass.EXTERNAL,
        mode=AgentMode.EXECUTION,
        preapproved=True,
        denied=True,
    )
    assert gate.decision is Decision.DENY


# -- the manager ---------------------------------------------------------


async def test_connecting_bridges_the_advertised_tools() -> None:
    connection = FakeConnection(tools=[McpToolDef(name="get_code"), McpToolDef(name="get_image")])
    manager = await manager_with(connection)

    assert connection.opened
    assert sorted(tool.name for tool in manager.tools()) == [
        "mcp__figma__get_code",
        "mcp__figma__get_image",
    ]


async def test_disabled_servers_are_not_connected() -> None:
    connection = FakeConnection()
    config = McpConfig(servers={"figma": http_server(enabled=False)})
    manager = McpManager(config=config, connection_factory=factory_for(connection))

    await manager.connect()

    assert not connection.opened
    assert manager.tools() == []
    assert manager.configured is False


async def test_denied_tools_are_never_bridged() -> None:
    """The escape hatch has to work before approval is ever asked."""
    connection = FakeConnection(tools=[McpToolDef(name="get_code"), McpToolDef(name="delete_file")])
    manager = await manager_with(connection, http_server(denied_tools=["delete_file"]))

    assert [tool.name for tool in manager.tools()] == ["mcp__figma__get_code"]


async def test_a_failed_server_does_not_end_the_session() -> None:
    connection = FakeConnection(fail_on_open="connection refused")
    ui = RecordingConsole()
    config = McpConfig(servers={"figma": http_server()})
    manager = McpManager(config=config, connection_factory=factory_for(connection))

    await manager.connect(ui)  # type: ignore[arg-type]

    assert manager.tools() == []
    assert connection.closed
    statuses = manager.statuses()
    assert statuses[0].ok is False
    assert "connection refused" in statuses[0].detail
    assert "unavailable" in ui.text


async def test_two_servers_offering_the_same_tool_both_survive() -> None:
    first = FakeConnection("alpha", tools=[McpToolDef(name="search")])
    second = FakeConnection("beta", tools=[McpToolDef(name="search")])
    connections = {"alpha": first, "beta": second}

    config = McpConfig(servers={"alpha": http_server(), "beta": http_server()})
    manager = McpManager(
        config=config,
        connection_factory=lambda name, cfg: connections[name],  # type: ignore[arg-type,return-value]
    )
    await manager.connect()

    assert sorted(tool.name for tool in manager.tools()) == [
        "mcp__alpha__search",
        "mcp__beta__search",
    ]


async def test_approval_reflects_the_stored_allowlist() -> None:
    manager = await manager_with(FakeConnection(), http_server(allowed_tools=["get_code"]))
    approval = manager.approval("mcp__figma__get_code")

    assert approval is not None
    assert approval.preapproved is True
    assert approval.server == "figma"
    assert approval.tool == "get_code"


async def test_approval_is_none_for_ordinary_tools() -> None:
    manager = await manager_with(FakeConnection())
    assert manager.approval("read_file") is None


async def test_remember_records_the_bare_tool_name() -> None:
    server = http_server()
    manager = await manager_with(FakeConnection(), server)

    manager.remember("mcp__figma__get_code")

    assert server.allowed_tools == ["get_code"]


async def test_remember_reports_honestly_when_it_cannot_persist() -> None:
    """Without a persist hook the choice lasts one session, and we say so."""
    manager = await manager_with(FakeConnection())
    assert manager.remember("mcp__figma__get_code") is False


async def test_remember_persists_through_the_hook() -> None:
    written: list[bool] = []
    manager = await manager_with(
        FakeConnection(), http_server(), persist=lambda: written.append(True)
    )

    assert manager.remember("mcp__figma__get_code") is True
    assert written == [True]


async def test_closing_releases_every_connection() -> None:
    connection = FakeConnection()
    manager = await manager_with(connection)

    await manager.aclose()

    assert connection.closed
    assert manager.tools() == []


async def test_context_block_names_the_servers_and_warns_about_their_output() -> None:
    manager = await manager_with(FakeConnection())
    block = manager.context_block()

    assert "figma" in block
    assert "mcp__figma__get_code" in block
    assert "instructions" in block


async def test_reconnecting_does_not_duplicate_a_server() -> None:
    """A REPL reuses one manager, so per-connect state must not accumulate.

    Left unreset, the prompt block named each surviving server once per request
    it had lived through -- context that grew with the length of the session.
    """
    connection = FakeConnection()
    manager = await manager_with(connection)

    await manager.aclose()
    await manager.connect()

    assert len(manager.statuses()) == 1
    assert manager.context_block().count("**figma**") == 1
    assert [tool.name for tool in manager.tools()] == ["mcp__figma__get_code"]


async def test_a_server_added_mid_session_is_picked_up() -> None:
    """`/mcp add` mutates the live config, so the next request must see it."""
    config = McpConfig()
    manager = McpManager(config=config, connection_factory=factory_for(FakeConnection()))
    assert manager.configured is False

    config.servers["figma"] = http_server()

    assert manager.configured is True
    await manager.connect()
    assert [tool.name for tool in manager.tools()] == ["mcp__figma__get_code"]


async def test_context_block_is_empty_with_no_servers() -> None:
    manager = McpManager(config=McpConfig())
    await manager.connect()
    assert manager.context_block() == ""


# -- registry integration ------------------------------------------------


async def registry_ctx(
    ctx: ToolContext, connection: FakeConnection, server: McpServerConfig | None = None
) -> ToolRegistry:
    manager = await manager_with(connection, server)
    ctx.mcp = manager
    ctx.config.mcp = manager.config
    registry = ToolRegistry(extra=manager.tools())
    return registry


async def test_bridged_tools_are_offered_to_the_model(ctx: ToolContext) -> None:
    registry = await registry_ctx(ctx, FakeConnection())
    names = [spec.name for spec in registry.exposed(AgentMode.PLANNING)]
    assert "mcp__figma__get_code" in names


async def test_allow_once_runs_without_remembering(ctx: ToolContext) -> None:
    connection = FakeConnection()
    server = http_server()
    registry = await registry_ctx(ctx, connection, server)
    ctx.ui = RecordingConsole(answers=[ALLOW_ONCE])  # type: ignore[assignment]

    result = await registry.execute(
        ToolUseBlock(id="1", name="mcp__figma__get_code", input={}), ctx
    )

    assert not result.is_error
    assert connection.calls
    assert server.allowed_tools == []


async def test_always_allow_is_remembered(ctx: ToolContext) -> None:
    server = http_server()
    registry = await registry_ctx(ctx, FakeConnection(), server)
    ctx.ui = RecordingConsole(answers=[ALLOW_ALWAYS])  # type: ignore[assignment]

    await registry.execute(ToolUseBlock(id="1", name="mcp__figma__get_code", input={}), ctx)

    assert server.allowed_tools == ["get_code"]


async def test_denying_blocks_the_call(ctx: ToolContext) -> None:
    connection = FakeConnection()
    registry = await registry_ctx(ctx, connection)
    ctx.ui = RecordingConsole(answers=[DENY_TOOL])  # type: ignore[assignment]

    result = await registry.execute(
        ToolUseBlock(id="1", name="mcp__figma__get_code", input={}), ctx
    )

    assert result.is_error
    assert not connection.calls
    assert "declined" in result.content


async def test_a_remembered_tool_is_not_asked_about_again(ctx: ToolContext) -> None:
    connection = FakeConnection()
    registry = await registry_ctx(ctx, connection, http_server(allowed_tools=["get_code"]))
    ui = RecordingConsole(answers=[DENY_TOOL])
    ctx.ui = ui  # type: ignore[assignment]

    result = await registry.execute(
        ToolUseBlock(id="1", name="mcp__figma__get_code", input={}), ctx
    )

    # The scripted "Deny" was never consumed, because nothing asked.
    assert not result.is_error
    assert connection.calls


async def test_a_denied_tool_cannot_be_called_even_if_bridged(ctx: ToolContext) -> None:
    """denied_tools normally hides a tool; the gate is the second line."""
    connection = FakeConnection()
    manager = await manager_with(connection, http_server())
    manager.config.servers["figma"].denied_tools.append("get_code")
    ctx.mcp = manager
    registry = ToolRegistry(extra=manager.tools())

    result = await registry.execute(
        ToolUseBlock(id="1", name="mcp__figma__get_code", input={}), ctx
    )

    assert result.is_error
    assert not connection.calls


async def test_bad_arguments_are_rejected_before_the_server_is_touched(
    ctx: ToolContext,
) -> None:
    connection = FakeConnection(
        tools=[
            McpToolDef(
                name="get_code",
                input_schema={"type": "object", "required": ["id"], "properties": {}},
            )
        ]
    )
    registry = await registry_ctx(ctx, connection, http_server(allowed_tools=["get_code"]))

    result = await registry.execute(
        ToolUseBlock(id="1", name="mcp__figma__get_code", input={}), ctx
    )

    assert result.is_error
    assert "id" in result.content
    assert not connection.calls


def test_dropping_external_tools_leaves_the_builtin_ones() -> None:
    """A REPL reuses its registry, so stale bridged tools must be removable."""
    connection = FakeConnection()
    registry = ToolRegistry(
        extra=[
            build_tool(
                connection=connection,  # type: ignore[arg-type]
                definition=McpToolDef(name="get_code"),
                qualified_name="mcp__figma__get_code",
                max_result_bytes=1024,
            )
        ]
    )
    assert "mcp__figma__get_code" in registry

    removed = registry.drop_class(ToolClass.EXTERNAL)

    assert removed == 1
    assert "mcp__figma__get_code" not in registry
    assert "read_file" in registry


# -- the SDK adapter's pure parts ----------------------------------------
#
# These need no server and no optional dependency: they are the translation
# layer between the wire shapes and Coderrr's own types.


class FakeGroup(Exception):
    """Stands in for an anyio/ExceptionGroup without needing 3.11+."""

    def __init__(self, message: str, exceptions: list[BaseException]) -> None:
        super().__init__(message)
        self.exceptions = exceptions


def test_exception_groups_are_unwrapped_to_the_real_cause() -> None:
    """A refused connection must not surface as "unhandled errors in a TaskGroup"."""
    group = FakeGroup(
        "unhandled errors in a TaskGroup (1 sub-exception)",
        [ConnectionRefusedError("All connection attempts failed")],
    )
    assert _reason(group) == "All connection attempts failed"


def test_nested_groups_are_unwrapped_and_deduplicated() -> None:
    inner = FakeGroup("group", [OSError("boom"), OSError("boom")])
    assert _reason(FakeGroup("outer", [inner])) == "boom"


def test_a_silent_exception_falls_back_to_its_type() -> None:
    assert _reason(ValueError()) == "ValueError"


def test_text_blocks_are_converted() -> None:
    block = _to_block({"type": "text", "text": "hello"})
    assert block.kind == "text"
    assert block.text == "hello"


def test_binary_blocks_keep_only_their_type() -> None:
    block = _to_block({"type": "image", "data": "base64...", "mimeType": "image/png"})
    assert block.kind == "image"
    assert block.mime == "image/png"
    # The payload is deliberately dropped rather than spent as tokens.
    assert block.text == ""


def test_embedded_resources_are_flattened() -> None:
    block = _to_block(
        {
            "type": "resource",
            "resource": {
                "text": "body",
                "mimeType": "text/plain",
                "uri": "file:///a.txt",
            },
        }
    )
    assert block.kind == "resource"
    assert block.text == "body"
    assert block.uri == "file:///a.txt"


def test_resource_links_carry_their_uri() -> None:
    block = _to_block({"type": "resource_link", "uri": "https://x/y"})
    assert block.kind == "resource"
    assert block.uri == "https://x/y"


def test_unknown_block_types_degrade_rather_than_raise() -> None:
    """A future content type must not break an otherwise fine tool call."""
    assert _to_block({"type": "hologram"}).kind == "other"


def test_malformed_resource_blocks_do_not_raise() -> None:
    assert _to_block({"type": "resource", "resource": "not-an-object"}).kind == "resource"


def test_tool_definitions_are_converted_from_wire_names() -> None:
    """The wire is camelCase; this is where that vocabulary stops."""
    definition = _to_definition(
        {
            "name": "get_code",
            "description": "d",
            "inputSchema": {"type": "object", "required": ["id"]},
            "title": "Get code",
            "annotations": {"readOnlyHint": True, "destructiveHint": False},
        }
    )

    assert definition.name == "get_code"
    assert definition.title == "Get code"
    assert definition.input_schema["required"] == ["id"]
    assert definition.read_only is True
    assert definition.advisory == "read-only"


def test_a_definition_without_a_schema_still_works() -> None:
    definition = _to_definition({"name": "ping"})
    assert definition.input_schema == {"type": "object"}
    assert definition.advisory == ""


def test_non_boolean_hints_are_ignored() -> None:
    """A hint is only a hint if it is actually a boolean."""
    definition = _to_definition({"name": "x", "annotations": {"readOnlyHint": "yes please"}})
    assert definition.read_only is None


def test_jsonrpc_errors_become_mcp_errors() -> None:
    with pytest.raises(McpError, match="Unknown tool"):
        _unwrap({"error": {"code": -32602, "message": "Unknown tool"}}, "tools/call")


def test_a_reply_with_no_result_is_an_error() -> None:
    with pytest.raises(McpError, match="neither"):
        _unwrap({"jsonrpc": "2.0", "id": 1}, "tools/list")


def test_results_pass_straight_through() -> None:
    assert _unwrap({"result": {"tools": []}}, "tools/list") == {"tools": []}


# -- the /mcp REPL flow --------------------------------------------------
#
# These are sync on purpose: handle_command calls asyncio.run() itself, which
# raises if a loop is already running.


def build_repl(
    workspace: Path,
    config: Config,
    monkeypatch: pytest.MonkeyPatch,
    *,
    answers: list[str] | None = None,
    confirm: bool | list[bool] = True,
    tools: list[str] | None = None,
    fails: str = "",
) -> tuple[Repl, RecordingConsole]:
    """A Repl whose MCP probing is faked and whose config never reaches disk."""

    async def fake_probe(name: str, server: McpServerConfig) -> list[str]:
        if fails:
            raise McpError(fails)
        return tools if tools is not None else ["get_code"]

    monkeypatch.setattr(mcp_setup, "probe", fake_probe)
    monkeypatch.setattr(repl_module, "save_config", lambda cfg: Path("/dev/null"))

    ui = RecordingConsole(answers=list(answers or []), confirm=confirm)
    instance = Repl(
        workspace=workspace,
        config=config,
        provider=FakeProvider([]),  # type: ignore[arg-type]
        ui=ui,  # type: ignore[arg-type]
    )
    return instance, ui


def test_mcp_add_from_a_pasted_url(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance, ui = build_repl(workspace, config, monkeypatch, answers=["figma"])

    instance.handle_command("/mcp add http://127.0.0.1:3845/mcp")

    server = config.mcp.servers["figma"]
    assert server.transport == "http"
    assert server.url == "http://127.0.0.1:3845/mcp"
    assert "1 tool(s)" in ui.text
    assert "mcp__figma__" in ui.text


def test_a_server_added_in_the_repl_reaches_the_running_session(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point of adding from inside the REPL: no restart."""
    instance, _ = build_repl(workspace, config, monkeypatch, answers=["figma"])
    assert instance.session.mcp.configured is False

    instance.handle_command("/mcp add http://127.0.0.1:3845/mcp")

    assert instance.session.mcp.configured is True


def test_mcp_add_asks_before_running_a_local_command(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance, ui = build_repl(workspace, config, monkeypatch, answers=["srv"], confirm=[False])

    instance.handle_command("/mcp add npx -y @some/server")

    assert config.mcp.servers == {}
    assert "outside Coderrr's sandbox" in ui.text


def test_mcp_add_saves_a_stdio_server_once_confirmed(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance, _ = build_repl(workspace, config, monkeypatch, answers=["srv"], confirm=[True])

    instance.handle_command("/mcp add npx -y @some/server")

    server = config.mcp.servers["srv"]
    assert server.transport == "stdio"
    assert server.command == "npx"
    assert server.args == ["-y", "@some/server"]


def test_mcp_add_reports_an_unreachable_server(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saving anyway is offered, because the app may just not be running yet."""
    instance, ui = build_repl(
        workspace,
        config,
        monkeypatch,
        answers=["figma"],
        confirm=[True],
        fails="All connection attempts failed",
    )

    instance.handle_command("/mcp add http://127.0.0.1:3845/mcp")

    assert "All connection attempts failed" in ui.text
    assert "figma" in config.mcp.servers


def test_mcp_add_refuses_a_duplicate_name(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.mcp.servers["figma"] = http_server()
    instance, ui = build_repl(workspace, config, monkeypatch, answers=["figma"])

    instance.handle_command("/mcp add http://other.example/mcp")

    assert config.mcp.servers["figma"].url == "http://127.0.0.1:3845/mcp"
    assert "already exists" in ui.text


def test_mcp_add_rejects_nonsense(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    instance, ui = build_repl(workspace, config, monkeypatch, answers=[""])

    instance.handle_command("/mcp add")

    assert config.mcp.servers == {}
    assert "Nothing added" in ui.text


def test_mcp_remove(workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    config.mcp.servers["figma"] = http_server()
    instance, ui = build_repl(workspace, config, monkeypatch)

    instance.handle_command("/mcp remove figma")

    assert config.mcp.servers == {}
    assert "Removed figma" in ui.text


def test_bare_mcp_lists_without_prompting_when_not_a_tty(
    workspace: Path, config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Piped input must not have its next line eaten by a menu."""
    config.mcp.servers["figma"] = http_server(allowed_tools=["get_code"])
    instance, ui = build_repl(workspace, config, monkeypatch, answers=["should-not-be-read"])

    instance.handle_command("/mcp")

    assert instance.interactive is False
    assert "table(1 rows)" in ui.text
    assert ui._answers == ["should-not-be-read"]


# -- name suggestion -----------------------------------------------------


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("https://mcp.notion.com/mcp", "notion"),
        ("https://mcp.linear.app/sse", "linear"),
        ("http://127.0.0.1:3845/mcp", ""),  # an IP says nothing useful
        ("npx -y @figma/mcp-server", "figma"),
        # The most specific word wins, which is what the usual
        # scope/server-<thing> package layouts call for.
        ("uvx mcp-server-sqlite", "sqlite"),
        ("npx -y @modelcontextprotocol/server-filesystem", "filesystem"),
    ],
)
def test_suggested_names(target: str, expected: str) -> None:
    assert mcp_setup.suggest_name(target.split()) == expected


def test_build_server_infers_the_transport() -> None:
    assert mcp_setup.build_server(["https://x.example/mcp"]).transport == "http"
    assert mcp_setup.build_server(["npx", "-y", "srv"]).transport == "stdio"


def test_build_server_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="URL or a command"):
        mcp_setup.build_server([])
    with pytest.raises(ValueError, match="not an http"):
        mcp_setup.build_server(["not-a-url"], transport="http")
    with pytest.raises(ValueError, match=r"must be 'http' or 'stdio'"):
        mcp_setup.build_server(["x"], transport="carrier-pigeon")


def test_header_pairs_are_parsed() -> None:
    assert mcp_setup.parse_pairs(["A=1", "B=x=y"], label="-H") == {"A": "1", "B": "x=y"}
    with pytest.raises(ValueError, match="KEY=VALUE"):
        mcp_setup.parse_pairs(["nope"], label="-H")


# -- configuration -------------------------------------------------------


def test_env_references_are_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIGMA_TOKEN", "secret")
    resolved, missing = expand_env_refs({"Authorization": "Bearer ${FIGMA_TOKEN}"})

    assert resolved == {"Authorization": "Bearer secret"}
    assert missing == []


def test_unset_env_references_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOPE", raising=False)
    resolved, missing = expand_env_refs({"Authorization": "Bearer ${NOPE}"})

    assert resolved == {"Authorization": "Bearer "}
    assert missing == ["NOPE"]


def test_a_server_needs_a_reachable_target() -> None:
    with pytest.raises(ValueError, match="url"):
        McpServerConfig(transport="http")
    with pytest.raises(ValueError, match="command"):
        McpServerConfig(transport="stdio")


def test_server_label_describes_the_target() -> None:
    assert http_server().label == "http://127.0.0.1:3845/mcp"
    stdio = McpServerConfig(transport="stdio", command="npx", args=["-y", "srv"])
    assert stdio.label == "npx -y srv"


def test_servers_survive_a_config_round_trip(tmp_path: Any) -> None:
    path = tmp_path / "config.toml"
    config = Config()
    config.mcp.servers["figma"] = http_server(allowed_tools=["get_code"])
    save_config(config, path)

    loaded = load_config(path)

    assert loaded.mcp.servers["figma"].url == "http://127.0.0.1:3845/mcp"
    assert loaded.mcp.servers["figma"].allowed_tools == ["get_code"]


def test_an_empty_mcp_table_is_not_written(tmp_path: Any) -> None:
    """Config files stay readable for the majority who use no MCP servers."""
    path = tmp_path / "config.toml"
    save_config(Config(), path)
    assert "mcp" not in path.read_text(encoding="utf-8")
