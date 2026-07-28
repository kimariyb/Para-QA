"""LangChain-based LLM utilities.

- ``build_chat_model``: ChatOpenAI factory for any OpenAI-compatible endpoint
  (OpenAI, DeepSeek, Qwen, vLLM, Xinference, Ollama) via env vars
  ``LLM_BASE_URL`` / ``LLM_API_KEY`` / ``LLM_MODEL``.
- ``PassageFakeChatModel``: deterministic offline model for ``--dry-run`` and
  unit tests. Fabricates evidence-grounded candidates so the whole pipeline
  can be exercised without an API key.
- ``UsageTracker``: LangChain callback accumulating token usage.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
_REASONING_EFFORTS = {"none", "low", "medium", "high"}


def reasoning_options(env_prefix: str = "QAC_LLM") -> dict[str, Any]:
    """Build provider-neutral no-reasoning options from non-secret env vars.

    ``reasoning_effort=none`` is the standard OpenAI-compatible request field.
    Providers that require a non-standard body can receive it through
    ``*_EXTRA_BODY_JSON`` (for example, ``{"thinking":{"type":"disabled"}}``).
    """
    effort = os.environ.get(f"{env_prefix}_REASONING_EFFORT", "none").strip().lower()
    if effort not in _REASONING_EFFORTS:
        raise ValueError(
            f"{env_prefix}_REASONING_EFFORT must be one of "
            f"{', '.join(sorted(_REASONING_EFFORTS))}"
        )
    options: dict[str, Any] = {"reasoning_effort": effort}
    raw_extra_body = os.environ.get(f"{env_prefix}_EXTRA_BODY_JSON", "").strip()
    if raw_extra_body:
        try:
            extra_body = json.loads(raw_extra_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{env_prefix}_EXTRA_BODY_JSON must be valid JSON") from exc
        if not isinstance(extra_body, dict):
            raise ValueError(f"{env_prefix}_EXTRA_BODY_JSON must encode an object")
        options["extra_body"] = extra_body
    return options


def extract_json(text: str) -> Any:
    """Best-effort extraction of a JSON value from an LLM response."""
    cleaned = _JSON_FENCE.sub("", text.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No valid JSON found in LLM response: {text[:200]!r}")


def build_chat_model(
    model: str | None = None,
    *,
    env_prefix: str = "QAC_LLM",
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 600,
    max_retries: int = 4,
    **kwargs: Any,
) -> BaseChatModel:
    """ChatOpenAI for any OpenAI-compatible endpoint, configured via env.

    Reads ``{env_prefix}_BASE_URL`` / ``{env_prefix}_API_KEY`` /
    ``{env_prefix}_MODEL`` (e.g. ``QAC_LLM_*`` for dataset generation or
    ``EVAL_LLM_*`` for RAG/evaluation). Falls back to the generic
    ``LLM_*`` variables when the prefixed ones are unset.
    """
    from langchain_openai import ChatOpenAI

    def _get(name: str, default: str = "") -> str:
        return (
            os.environ.get(f"{env_prefix}_{name}")
            or os.environ.get(f"LLM_{name}")
            or default
        )

    base_url = _get("BASE_URL").rstrip("/")
    api_key = _get("API_KEY")
    if not base_url or not api_key:
        raise RuntimeError(
            f"{env_prefix}_BASE_URL and {env_prefix}_API_KEY must be set "
            "(OpenAI-compatible endpoint)."
        )
    # Per-endpoint overrides (e.g. Moonshot kimi-k2 reasoner quirks).
    temp_env = _get("TEMPERATURE")
    if temp_env:
        try:
            temperature = float(temp_env)
        except ValueError:
            pass
    max_tokens_env = _get("MAX_TOKENS")
    if max_tokens_env:
        try:
            max_tokens = int(max_tokens_env)
        except ValueError:
            pass
    timeout_env = _get("TIMEOUT")
    if timeout_env:
        try:
            timeout = int(timeout_env)
        except ValueError:
            pass
    reasoning = reasoning_options(env_prefix)
    return ChatOpenAI(
        model=model or _get("MODEL", "gpt-4o-mini"),
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        **reasoning,
        **kwargs,
    )


class UsageTracker(BaseCallbackHandler):
    """Accumulate token usage across LangChain LLM calls."""

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        self.calls += 1
        for generations in getattr(response, "generations", []):
            for generation in generations:
                usage = getattr(generation.message, "usage_metadata", None) or {}
                self.input_tokens += usage.get("input_tokens", 0)
                self.output_tokens += usage.get("output_tokens", 0)


class PassageFakeChatModel(BaseChatModel):
    """Deterministic offline stand-in for dry-runs and tests.

    Reads the evidence passage between ``<passage>``/``</passage>`` markers in
    the user message and fabricates candidates whose ``evidence_span`` is a
    verbatim sentence, so grounding checks pass offline.
    """

    @property
    def _llm_type(self) -> str:
        return "passage-fake"

    def _generate(self, messages: list[BaseMessage], **kwargs: Any) -> ChatResult:
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self._respond(messages)))]
        )

    def _respond(self, messages: list[BaseMessage]) -> str:
        system = next((str(m.content) for m in messages if m.type == "system"), "")
        user = str(messages[-1].content) if messages else ""
        match = re.search(r"<passage>\s*(.*?)\s*</passage>", user, re.DOTALL)
        passage = match.group(1) if match else ""
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", passage)
            if len(s.strip()) > 40
        ]

        if "judge" in system.lower():
            return json.dumps(
                {
                    "answerable": True,
                    "supported": True,
                    "self_contained": True,
                    "reason": "mock verdict",
                }
            )
        if "answer the question" in system.lower():
            return sentences[0] if sentences else "UNANSWERABLE"

        items = [
            {
                "question": "According to the passage, what is stated in: "
                f"\"{sentence[:60]}...\"?",
                "answer": sentence,
                "evidence_span": sentence,
                "qtype": "factoid" if i == 0 else "reasoning",
                "difficulty": "easy" if i == 0 else "medium",
            }
            for i, sentence in enumerate(sentences[:2])
        ]
        return json.dumps({"items": items}, ensure_ascii=False)

    def with_structured_output(self, schema: type[BaseModel], **kwargs: Any) -> Runnable:
        """Parse the fake's JSON responses into the requested Pydantic schema."""
        return self | RunnableLambda(
            lambda message: schema.model_validate(extract_json(message.content))
        )
