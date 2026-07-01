from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from peas_agent.llm_content import extract_answer_text, iter_content_blocks

from agent_dungeon.core.bootstrap_config import build_effective_config

BRAIN_MODEL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "ollama_cloud@minimax-m3:cloud",
        "openai@gpt-4o-mini",
    }
)

DEFAULT_BRAIN_MODEL = "ollama_cloud@minimax-m3:cloud"

_BRAIN_CONNECTION_ERROR = "Brain 尚未連線，請聯絡老師。"


def model_in_allowlist(model: str) -> bool:
    return model.strip() in BRAIN_MODEL_ALLOWLIST


def _reasoning_text_from_block(block: dict[str, Any]) -> str:
    reasoning = block.get("reasoning")
    if isinstance(reasoning, str) and reasoning:
        return reasoning
    summary = block.get("summary")
    if isinstance(summary, str) and summary:
        return summary
    if isinstance(summary, list):
        parts: list[str] = []
        for item in summary:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
            elif isinstance(item, str) and item:
                parts.append(item)
        return "".join(parts)
    return ""


def extract_reasoning_text(message: AIMessage) -> str:
    parts: list[str] = []
    for block in iter_content_blocks(message):
        if block.get("type") == "reasoning":
            text = _reasoning_text_from_block(block)
            if text:
                parts.append(text)
    return "".join(parts).strip()


def build_chat_client(config: dict[str, Any], *, model: str) -> ChatOpenAI:
    llm_cfg = config.get("llm", {})
    if not isinstance(llm_cfg, dict):
        llm_cfg = {}
    api_key = str(llm_cfg.get("api_key") or "").strip()
    if not api_key:
        raise RuntimeError(_BRAIN_CONNECTION_ERROR)

    try:
        request_timeout = float(llm_cfg.get("request_timeout", 120))
    except (TypeError, ValueError):
        request_timeout = 120.0

    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "model": model,
        "temperature": llm_cfg.get("temperature", 0.2),
        "timeout": request_timeout,
    }
    base_url = str(llm_cfg.get("base_url") or "").strip()
    if base_url:
        kwargs["base_url"] = base_url

    if llm_cfg.get("use_responses_api") is True:
        kwargs["use_responses_api"] = True
        output_version = str(llm_cfg.get("output_version") or "").strip()
        if output_version:
            kwargs["output_version"] = output_version
        reasoning_cfg = llm_cfg.get("reasoning")
        if isinstance(reasoning_cfg, dict) and reasoning_cfg:
            kwargs["reasoning"] = dict(reasoning_cfg)

    return ChatOpenAI(**kwargs)


def invoke_llm_response(
    *,
    config: dict[str, Any],
    model: str,
    message: str,
) -> tuple[str, str]:
    stripped = message.strip()
    if not stripped:
        raise RuntimeError("invoke 需要非空訊息。")
    client = build_chat_client(config, model=model.strip())
    response = client.invoke([HumanMessage(content=stripped)])
    if not isinstance(response, AIMessage):
        content = getattr(response, "content", "")
        text = content.strip() if isinstance(content, str) else str(content).strip()
        if not text:
            raise RuntimeError("Brain 沒有回覆，請稍後再試。")
        return text, ""

    answer = extract_answer_text(response)
    if not answer:
        raise RuntimeError("Brain 沒有回覆，請稍後再試。")
    return answer, extract_reasoning_text(response)


def invoke_llm_message(*, google_sub: str | None, model: str, message: str) -> str:
    if google_sub is None:
        raise RuntimeError(_BRAIN_CONNECTION_ERROR)
    if not model_in_allowlist(model):
        raise RuntimeError(f"不支援的 model：{model!r}。請從挑戰說明中的清單選擇。")
    config = build_effective_config(google_sub)
    answer, _ = invoke_llm_response(config=config, model=model, message=message)
    return answer


def make_brain_class(
    *,
    google_sub: str | None,
    config_builder: Callable[[str], dict[str, Any]] | None = None,
) -> type:
    """Forge 沙箱注入用：學生寫 Brain(model=...) 與 llm.invoke(...)。"""

    builder = config_builder or build_effective_config

    class Brain:
        def __init__(self, model: str) -> None:
            self.model = str(model).strip()
            self.last_reasoning = ""
            if not self.model:
                raise ValueError("model 不可為空")
            if not model_in_allowlist(self.model):
                raise ValueError(
                    f"不支援的 model：{self.model!r}。請從挑戰說明中的清單選擇。"
                )

        def invoke(self, message: str) -> str:
            if google_sub is None:
                raise RuntimeError(_BRAIN_CONNECTION_ERROR)
            answer, reasoning = invoke_llm_response(
                config=builder(google_sub),
                model=self.model,
                message=str(message),
            )
            self.last_reasoning = reasoning
            return answer

    return Brain


def render_standalone_brain_module() -> str:
    allowlist_repr = ", ".join(repr(item) for item in sorted(BRAIN_MODEL_ALLOWLIST))
    return f'''\
"""Standalone Brain runtime — 由 Agent Dungeon 畢業匯出產生。"""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

load_dotenv()

BRAIN_MODEL_ALLOWLIST: frozenset[str] = frozenset(
    {{
        {allowlist_repr}
    }}
)

DEFAULT_BRAIN_MODEL = {DEFAULT_BRAIN_MODEL!r}


def _reasoning_text_from_block(block: dict[str, Any]) -> str:
    reasoning = block.get("reasoning")
    if isinstance(reasoning, str) and reasoning:
        return reasoning
    summary = block.get("summary")
    if isinstance(summary, str) and summary:
        return summary
    if isinstance(summary, list):
        parts: list[str] = []
        for item in summary:
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
            elif isinstance(item, str) and item:
                parts.append(item)
        return "".join(parts)
    return ""


def _iter_content_blocks(message: AIMessage) -> list[dict[str, Any]]:
    blocks = getattr(message, "content_blocks", None)
    if blocks:
        return [block for block in blocks if isinstance(block, dict)]
    content = message.content
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def _extract_answer_text(message: AIMessage) -> str:
    parts: list[str] = []
    saw_blocks = False
    for block in _iter_content_blocks(message):
        saw_blocks = True
        if block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
    if saw_blocks:
        return "".join(parts).strip()
    content = message.content
    return content.strip() if isinstance(content, str) else str(content).strip()


def _extract_reasoning_text(message: AIMessage) -> str:
    parts: list[str] = []
    for block in _iter_content_blocks(message):
        if block.get("type") == "reasoning":
            text = _reasoning_text_from_block(block)
            if text:
                parts.append(text)
    return "".join(parts).strip()


def _build_client(*, model: str) -> ChatOpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("請在 .env 設定 OPENAI_API_KEY。")
    kwargs: dict[str, Any] = {{
        "api_key": api_key,
        "model": model,
        "temperature": float(os.environ.get("BRAIN_TEMPERATURE", "0.2")),
        "timeout": float(os.environ.get("BRAIN_REQUEST_TIMEOUT", "120")),
        "use_responses_api": True,
        "output_version": os.environ.get("BRAIN_OUTPUT_VERSION", "responses/v1"),
    }}
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    if base_url:
        kwargs["base_url"] = base_url
    effort = os.environ.get("BRAIN_REASONING_EFFORT", "").strip()
    if effort:
        kwargs["reasoning"] = {{"effort": effort, "summary": "auto"}}
    return ChatOpenAI(**kwargs)


class Brain:
    def __init__(self, model: str) -> None:
        self.model = str(model).strip()
        self.last_reasoning = ""
        if not self.model:
            raise ValueError("model 不可為空")
        if self.model not in BRAIN_MODEL_ALLOWLIST:
            raise ValueError(
                f"不支援的 model：{{self.model!r}}。請從 README 中的清單選擇。"
            )

    def invoke(self, message: str) -> str:
        stripped = str(message).strip()
        if not stripped:
            raise RuntimeError("invoke 需要非空訊息。")
        client = _build_client(model=self.model)
        response = client.invoke([HumanMessage(content=stripped)])
        if not isinstance(response, AIMessage):
            content = getattr(response, "content", "")
            text = content.strip() if isinstance(content, str) else str(content).strip()
            if not text:
                raise RuntimeError("Brain 沒有回覆，請稍後再試。")
            self.last_reasoning = ""
            return text
        answer = _extract_answer_text(response)
        if not answer:
            raise RuntimeError("Brain 沒有回覆，請稍後再試。")
        self.last_reasoning = _extract_reasoning_text(response)
        return answer
'''
