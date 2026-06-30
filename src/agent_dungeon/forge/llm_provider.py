from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from agent_dungeon.core.bootstrap_config import build_effective_config

# Forge 挑戰／Lab 可選 model（router 格式；端點由平台 config 提供，不對學生揭露）
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


def _build_chat_client(
    config: dict[str, Any],
    *,
    model: str,
    for_forge: bool = False,
) -> ChatOpenAI:
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

    # Forge 中欄：固定 Chat Completions，與右欄 Agent（Responses API）分離
    if not for_forge and llm_cfg.get("use_responses_api") is True:
        kwargs["use_responses_api"] = True
        output_version = str(llm_cfg.get("output_version") or "").strip()
        if output_version:
            kwargs["output_version"] = output_version
        reasoning_cfg = llm_cfg.get("reasoning")
        if isinstance(reasoning_cfg, dict) and reasoning_cfg:
            kwargs["reasoning"] = dict(reasoning_cfg)

    return ChatOpenAI(**kwargs)


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
        return "".join(parts).strip()
    return str(content or "").strip()


def invoke_llm_message(*, google_sub: str | None, model: str, message: str) -> str:
    if google_sub is None:
        raise RuntimeError(_BRAIN_CONNECTION_ERROR)
    if not model_in_allowlist(model):
        raise RuntimeError(f"不支援的 model：{model!r}。請從挑戰說明中的清單選擇。")
    stripped = message.strip()
    if not stripped:
        raise RuntimeError("invoke 需要非空訊息。")

    config = build_effective_config(google_sub)
    client = _build_chat_client(config, model=model.strip(), for_forge=True)
    response = client.invoke([HumanMessage(content=stripped)])
    content = _message_text(getattr(response, "content", ""))
    if not content:
        raise RuntimeError("Brain 沒有回覆，請稍後再試。")
    return content


def make_brain_class(*, google_sub: str | None) -> type:
    """Forge 沙箱注入用：學生寫 Brain(model=...) 與 llm.invoke(...)。"""

    class Brain:
        def __init__(self, model: str) -> None:
            self.model = str(model).strip()
            if not self.model:
                raise ValueError("model 不可為空")
            if not model_in_allowlist(self.model):
                raise ValueError(
                    f"不支援的 model：{self.model!r}。請從挑戰說明中的清單選擇。"
                )

        def invoke(self, message: str) -> str:
            return invoke_llm_message(
                google_sub=google_sub,
                model=self.model,
                message=str(message),
            )

    return Brain
