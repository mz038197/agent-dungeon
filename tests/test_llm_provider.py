from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agent_dungeon.forge.llm_provider import (
    _build_chat_client,
    _message_text,
    invoke_llm_message,
)


def test_forge_client_uses_chat_completions_only() -> None:
    config = {
        "llm": {
            "api_key": "test-key",
            "use_responses_api": True,
            "output_version": "responses/v1",
            "reasoning": {"effort": "medium", "summary": "auto"},
        }
    }
    with patch("agent_dungeon.forge.llm_provider.ChatOpenAI") as mock_cls:
        _build_chat_client(config, model="openai@gpt-4o-mini", for_forge=True)
        kwargs = mock_cls.call_args.kwargs
    assert "use_responses_api" not in kwargs
    assert "output_version" not in kwargs
    assert "reasoning" not in kwargs
    assert kwargs["api_key"] == "test-key"
    assert kwargs["model"] == "openai@gpt-4o-mini"


def test_non_forge_client_can_enable_responses_api() -> None:
    config = {
        "llm": {
            "api_key": "test-key",
            "use_responses_api": True,
            "output_version": "responses/v1",
            "reasoning": {"effort": "low", "summary": "auto"},
        }
    }
    with patch("agent_dungeon.forge.llm_provider.ChatOpenAI") as mock_cls:
        _build_chat_client(config, model="openai@gpt-4o-mini", for_forge=False)
        kwargs = mock_cls.call_args.kwargs
    assert kwargs["use_responses_api"] is True
    assert kwargs["output_version"] == "responses/v1"
    assert kwargs["reasoning"] == {"effort": "low", "summary": "auto"}


def test_message_text_prefers_plain_string() -> None:
    assert _message_text("你好") == "你好"


def test_message_text_extracts_text_blocks() -> None:
    content = [
        {"type": "reasoning", "summary": [{"text": "hidden"}]},
        {"type": "text", "text": "可見回答"},
    ]
    assert _message_text(content) == "可見回答"


def test_invoke_llm_message_returns_plain_text() -> None:
    mock_client = MagicMock()
    mock_client.invoke.return_value = AIMessage(content="Python 是一種程式語言。")
    with patch(
        "agent_dungeon.forge.llm_provider.build_effective_config",
        return_value={"llm": {"api_key": "k"}},
    ):
        with patch(
            "agent_dungeon.forge.llm_provider._build_chat_client",
            return_value=mock_client,
        ) as mock_build:
            result = invoke_llm_message(
                google_sub="sub-a",
                model="openai@gpt-4o-mini",
                message="Python 是什麼？",
            )
    mock_build.assert_called_once()
    assert mock_build.call_args.kwargs["for_forge"] is True
    assert result == "Python 是一種程式語言。"


def test_invoke_llm_message_requires_login() -> None:
    with pytest.raises(RuntimeError, match="Brain 尚未連線"):
        invoke_llm_message(
            google_sub=None,
            model="openai@gpt-4o-mini",
            message="hi",
        )
