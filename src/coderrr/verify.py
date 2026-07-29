"""LLM-based write verification.

Runs a second, independent model call over a proposed change and asks whether it
is valid and safe. This catches truncated files, wrong-file edits, accidental
deletions of unrelated code, and obvious injected secrets.

Scope note: this is a *correctness* check, not the security boundary. Path
containment lives in :mod:`coderrr.policy.paths` as deterministic code, because
a model can be argued out of a judgement and a path check cannot.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from coderrr.config import VerifyConfig
from coderrr.llm.base import Provider, ProviderError, collect
from coderrr.llm.types import Message

VERIFY_SYSTEM = """\
You are a code review gate. You receive a proposed file write and must judge \
whether applying it is safe and correct.

Reject when you see:
- Truncated or obviously incomplete content (cut mid-statement, trailing "...")
- Content that does not match the stated file path or language
- Destruction of substantial unrelated code with no replacement
- Hardcoded credentials, API keys, or private keys
- Obvious syntax errors

Accept ordinary code, including work-in-progress that is internally coherent.
Do not reject on style, formatting, or personal preference.

Respond with ONLY a JSON object:
{"verdict": "accept" | "reject", "reason": "<one sentence>"}
"""


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    reason: str = ""
    #: True when verification was skipped or could not run; callers treat this as
    #: non-blocking so a verifier outage never wedges the agent.
    skipped: bool = False

    @property
    def blocked(self) -> bool:
        return not self.accepted and not self.skipped


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

#: Only send the head and tail of large files -- the middle rarely changes the
#: verdict and sending it is expensive.
_EXCERPT = 6000


def _excerpt(text: str) -> str:
    if len(text) <= _EXCERPT * 2:
        return text
    return (
        f"{text[:_EXCERPT]}\n"
        f"... [{len(text) - _EXCERPT * 2} characters elided] ...\n"
        f"{text[-_EXCERPT:]}"
    )


class Verifier:
    """Wraps a provider call with the verification prompt."""

    def __init__(
        self,
        provider: Provider,
        config: VerifyConfig,
        *,
        fallback_model: str,
    ) -> None:
        self.provider = provider
        self.config = config
        self.model = config.model or fallback_model

    def applies(self, *, is_write: bool) -> bool:
        if self.config.mode == "off":
            return False
        if self.config.mode == "writes_only":
            return is_write
        return True

    async def check(
        self,
        *,
        path: str,
        before: str,
        after: str,
        intent: str = "",
    ) -> Verdict:
        """Judge a single proposed write."""
        if not self.applies(is_write=True):
            return Verdict(accepted=True, skipped=True, reason="verification disabled")

        action = "CREATE" if not before else "REPLACE"
        prompt = (
            f"File: {path}\n"
            f"Operation: {action}\n"
            f"Stated intent: {intent or '(none given)'}\n\n"
            f"--- PROPOSED CONTENT ---\n{_excerpt(after)}\n"
        )
        if before:
            prompt += f"\n--- CURRENT CONTENT (being replaced) ---\n{_excerpt(before)}\n"

        try:
            response = await collect(
                self.provider.stream(
                    system=VERIFY_SYSTEM,
                    messages=[Message.user_text(prompt)],
                    tools=[],
                    model=self.model,
                    max_tokens=300,
                    temperature=self.config.temperature,
                )
            )
        except ProviderError as exc:
            # A verifier outage must not block legitimate work.
            return Verdict(accepted=True, skipped=True, reason=f"verifier unavailable: {exc}")

        return self._parse(response.text())

    @staticmethod
    def _parse(text: str) -> Verdict:
        match = _JSON_RE.search(text)
        if match is None:
            return Verdict(accepted=True, skipped=True, reason="verifier returned no verdict")
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return Verdict(accepted=True, skipped=True, reason="verifier returned invalid JSON")

        verdict = str(payload.get("verdict", "")).strip().lower()
        reason = str(payload.get("reason", "")).strip()
        if verdict == "reject":
            return Verdict(accepted=False, reason=reason or "rejected by verifier")
        return Verdict(accepted=True, reason=reason)


class NullVerifier(Verifier):
    """Used when verification is disabled or in tests."""

    def __init__(self) -> None:
        self.config = VerifyConfig(mode="off")
        self.model = ""

    def applies(self, *, is_write: bool) -> bool:
        return False

    async def check(
        self,
        *,
        path: str,
        before: str,
        after: str,
        intent: str = "",
    ) -> Verdict:
        return Verdict(accepted=True, skipped=True, reason="verification disabled")
