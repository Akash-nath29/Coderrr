"""Provider adapter wire-format tests.

Each adapter is exercised against recorded SSE fixtures so the translation into
our normalized block model is pinned down without a network call.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from coderrr.llm import build_provider
from coderrr.llm.anthropic import AnthropicProvider
from coderrr.llm.base import ProviderError, collect
from coderrr.llm.google import GoogleProvider
from coderrr.llm.openai_compat import OpenAICompatProvider
from coderrr.llm.types import (
    Message,
    TextBlock,
    ToolClass,
    ToolResultBlock,
    ToolSpec,
    ToolUseBlock,
)

TOOL = ToolSpec(
    name="read_file",
    description="Read a file",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
    klass=ToolClass.READ,
)


def sse(*chunks: object) -> str:
    lines = []
    for chunk in chunks:
        payload = chunk if isinstance(chunk, str) else json.dumps(chunk)
        lines.append(f"data: {payload}\n\n")
    return "".join(lines)


# -- OpenAI-compatible ---------------------------------------------------


@respx.mock
async def test_openai_text_stream() -> None:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=sse(
                {"choices": [{"delta": {"content": "Hel"}}]},
                {"choices": [{"delta": {"content": "lo"}}]},
                {
                    "choices": [{"delta": {}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 7, "completion_tokens": 3},
                },
                "[DONE]",
            ),
        )
    )
    provider = OpenAICompatProvider(api_key="sk-test")
    response = await collect(
        provider.stream(system="s", messages=[Message.user_text("hi")], tools=[], model="gpt-4o")
    )
    assert response.text() == "Hello"
    assert response.stop_reason == "end_turn"
    assert response.usage.input_tokens == 7


@respx.mock
async def test_openai_tool_call_fragments_reassemble() -> None:
    """id and name arrive on the first fragment only; arguments stream after."""
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=sse(
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {"name": "read_file", "arguments": ""},
                                    }
                                ]
                            }
                        }
                    ]
                },
                {
                    "choices": [
                        {"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"pa'}}]}}
                    ]
                },
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {"index": 0, "function": {"arguments": 'th": "a.py"}'}}
                                ]
                            }
                        }
                    ]
                },
                {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
                "[DONE]",
            ),
        )
    )
    provider = OpenAICompatProvider(api_key="sk-test")
    response = await collect(
        provider.stream(
            system="s", messages=[Message.user_text("hi")], tools=[TOOL], model="gpt-4o"
        )
    )
    assert response.stop_reason == "tool_use"
    calls = response.tool_uses()
    assert len(calls) == 1
    assert calls[0].name == "read_file"
    assert calls[0].input == {"path": "a.py"}


@respx.mock
async def test_openai_parallel_tool_calls() -> None:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=sse(
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "c0",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": '{"path":"a"}',
                                        },
                                    },
                                    {
                                        "index": 1,
                                        "id": "c1",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": '{"path":"b"}',
                                        },
                                    },
                                ]
                            }
                        }
                    ]
                },
                {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
                "[DONE]",
            ),
        )
    )
    provider = OpenAICompatProvider(api_key="sk-test")
    response = await collect(provider.stream(system="", messages=[], tools=[TOOL], model="gpt-4o"))
    assert [c.input["path"] for c in response.tool_uses()] == ["a", "b"]


@respx.mock
async def test_ollama_tool_call_without_finish_reason() -> None:
    """Ollama often omits finish_reason; emitted calls still mean tool_use."""
    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            text=sse(
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "c0",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": '{"path":"x"}',
                                        },
                                    }
                                ]
                            }
                        }
                    ]
                },
                "[DONE]",
            ),
        )
    )
    provider = build_provider("ollama")
    response = await collect(
        provider.stream(system="", messages=[], tools=[TOOL], model="gemma4:31b-cloud")
    )
    assert response.stop_reason == "tool_use"


@respx.mock
async def test_openai_http_error_becomes_provider_error() -> None:
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(401, text='{"error":"bad key"}')
    )
    provider = OpenAICompatProvider(api_key="sk-bad")
    with pytest.raises(ProviderError, match="401"):
        await collect(provider.stream(system="", messages=[], tools=[], model="gpt-4o"))


def test_openai_message_translation_splits_tool_results() -> None:
    """Tool results become standalone role:tool messages."""
    from coderrr.llm.openai_compat import _messages_payload

    payload = _messages_payload(
        [
            Message.user_text("read it"),
            Message(role="assistant", content=[ToolUseBlock("c1", "read_file", {"path": "a"})]),
            Message(role="user", content=[ToolResultBlock("c1", "file body")]),
        ]
    )
    assert payload[0]["role"] == "user"
    assert payload[1]["role"] == "assistant"
    assert payload[1]["tool_calls"][0]["id"] == "c1"
    assert payload[2] == {"role": "tool", "tool_call_id": "c1", "content": "file body"}


# -- Anthropic -----------------------------------------------------------


@respx.mock
async def test_anthropic_text_and_tool_stream() -> None:
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            text=sse(
                {
                    "type": "message_start",
                    "message": {"usage": {"input_tokens": 12, "output_tokens": 0}},
                },
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "Reading."},
                },
                {
                    "type": "content_block_start",
                    "index": 1,
                    "content_block": {"type": "tool_use", "id": "tu_1", "name": "read_file"},
                },
                {
                    "type": "content_block_delta",
                    "index": 1,
                    "delta": {"type": "input_json_delta", "partial_json": '{"path":'},
                },
                {
                    "type": "content_block_delta",
                    "index": 1,
                    "delta": {"type": "input_json_delta", "partial_json": '"a.py"}'},
                },
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "tool_use"},
                    "usage": {"output_tokens": 25},
                },
            ),
        )
    )
    provider = AnthropicProvider(api_key="sk-ant-test")
    response = await collect(
        provider.stream(system="s", messages=[], tools=[TOOL], model="claude-sonnet-4")
    )
    assert response.text() == "Reading."
    assert response.stop_reason == "tool_use"
    assert response.tool_uses()[0].input == {"path": "a.py"}
    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 25


@respx.mock
async def test_anthropic_sends_system_out_of_band() -> None:
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, text=sse({"type": "message_stop"}))
    )
    provider = AnthropicProvider(api_key="k")
    await collect(provider.stream(system="be careful", messages=[], tools=[], model="m"))
    body = json.loads(route.calls[0].request.content)
    assert body["system"] == "be careful"
    assert "anthropic-version" in route.calls[0].request.headers


# -- Google --------------------------------------------------------------


@respx.mock
async def test_google_function_call_arrives_complete() -> None:
    """Gemini sends whole args objects, not streamed JSON fragments."""
    respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:streamGenerateContent"
    ).mock(
        return_value=httpx.Response(
            200,
            text=sse(
                {"candidates": [{"content": {"parts": [{"text": "Looking."}]}}]},
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "functionCall": {
                                            "name": "read_file",
                                            "args": {"path": "a.py"},
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                    "usageMetadata": {"promptTokenCount": 9, "candidatesTokenCount": 4},
                },
            ),
        )
    )
    provider = GoogleProvider(api_key="k")
    response = await collect(
        provider.stream(system="", messages=[], tools=[TOOL], model="gemini-2.0-flash")
    )
    assert response.text() == "Looking."
    assert response.stop_reason == "tool_use"
    assert response.tool_uses()[0].input == {"path": "a.py"}


def test_google_maps_results_by_name_not_id() -> None:
    """Gemini matches functionResponse by name, so names are recovered."""
    from coderrr.llm.google import _contents_payload

    payload = _contents_payload(
        [
            Message(role="assistant", content=[ToolUseBlock("c1", "read_file", {"path": "a"})]),
            Message(role="user", content=[ToolResultBlock("c1", "body")]),
        ]
    )
    assert payload[0]["role"] == "model"
    assert payload[1]["parts"][0]["functionResponse"]["name"] == "read_file"


def test_google_strips_unsupported_schema_keys() -> None:
    from coderrr.llm.google import _tools_payload

    spec = ToolSpec(
        name="t",
        description="d",
        input_schema={
            "type": "object",
            "title": "Drop me",
            "additionalProperties": False,
            "properties": {"x": {"type": "string", "default": "y"}},
        },
        klass=ToolClass.READ,
    )
    params = _tools_payload([spec])[0]["functionDeclarations"][0]["parameters"]
    assert "title" not in params
    assert "additionalProperties" not in params
    assert "default" not in params["properties"]["x"]


# -- factory -------------------------------------------------------------


def test_openrouter_and_ollama_share_the_openai_adapter() -> None:
    assert isinstance(build_provider("openrouter", api_key="k"), OpenAICompatProvider)
    assert isinstance(build_provider("ollama"), OpenAICompatProvider)
    assert isinstance(build_provider("openai", api_key="k"), OpenAICompatProvider)


def test_missing_key_is_rejected_up_front() -> None:
    with pytest.raises(ProviderError, match="requires an API key"):
        build_provider("anthropic")


def test_unknown_provider_lists_alternatives() -> None:
    with pytest.raises(ProviderError, match="Available"):
        build_provider("not-a-provider")


def test_ollama_needs_no_key() -> None:
    assert build_provider("ollama") is not None


# -- collector -----------------------------------------------------------


async def test_collect_tolerates_malformed_tool_json() -> None:
    """Bad JSON yields empty args; schema validation then gives the model a
    recoverable error rather than crashing the loop."""
    from coderrr.llm.types import MessageStop, ToolUseDelta, ToolUseStart, Usage

    async def stream():  # type: ignore[no-untyped-def]
        yield ToolUseStart(id="c1", name="read_file")
        yield ToolUseDelta(id="c1", partial_json="{not json")
        yield MessageStop(stop_reason="tool_use", usage=Usage())

    response = await collect(stream())
    assert response.tool_uses()[0].input == {}


async def test_collect_orders_blocks_text_then_tools() -> None:
    from coderrr.llm.types import MessageStop, TextDelta, ToolUseDelta, ToolUseStart, Usage

    async def stream():  # type: ignore[no-untyped-def]
        yield TextDelta("thinking")
        yield ToolUseStart(id="c1", name="read_file")
        yield ToolUseDelta(id="c1", partial_json='{"path":"a"}')
        yield MessageStop(stop_reason="tool_use", usage=Usage())

    response = await collect(stream())
    assert isinstance(response.content[0], TextBlock)
    assert isinstance(response.content[1], ToolUseBlock)
