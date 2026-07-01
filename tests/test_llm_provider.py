from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agent_dungeon.forge.adapters.brain import (
    build_chat_client,
    extract_reasoning_text,
    invoke_llm_message,
)
from agent_dungeon.forge.llm_provider import invoke_llm_message as invoke_public


def test_forge_client_enables_responses_api_from_config() -> None:
    config = {
        "llm": {
            "api_key": "test-key",
            "use_responses_api": True,
            "output_version": "responses/v1",
            "reasoning": {"effort": "medium", "summary": "auto"},
        }
    }
    with patch("agent_dungeon.forge.adapters.brain.ChatOpenAI") as mock_cls:
        build_chat_client(config, model="openai@gpt-4o-mini")
        kwargs = mock_cls.call_args.kwargs
    assert kwargs["use_responses_api"] is True
    assert kwargs["output_version"] == "responses/v1"
    assert kwargs["reasoning"] == {"effort": "medium", "summary": "auto"}
    assert kwargs["api_key"] == "test-key"
    assert kwargs["model"] == "openai@gpt-4o-mini"


def test_extract_reasoning_text_reads_reasoning_blocks() -> None:
    message = AIMessage(
        content=[
            {"type": "reasoning", "reasoning": "先想想"},
            {"type": "text", "text": "答案"},
        ]
    )
    assert extract_reasoning_text(message) == "先想想"


def test_invoke_llm_message_uses_extract_answer_text() -> None:
    mock_client = MagicMock()
    mock_client.invoke.return_value = AIMessage(
        content=[
            {"type": "reasoning", "reasoning": "hidden"},
            {"type": "text", "text": "Python 是一種程式語言。"},
        ]
    )
    with patch(
        "agent_dungeon.forge.adapters.brain.build_effective_config",
        return_value={"llm": {"api_key": "k", "use_responses_api": True}},
    ):
        with patch(
            "agent_dungeon.forge.adapters.brain.build_chat_client",
            return_value=mock_client,
        ):
            result = invoke_public(
                google_sub="sub-a",
                model="openai@gpt-4o-mini",
                message="Python 是什麼？",
            )
    assert result == "Python 是一種程式語言。"


def test_invoke_llm_message_requires_login() -> None:
    with pytest.raises(RuntimeError, match="Brain 尚未連線"):
        invoke_llm_message(
            google_sub=None,
            model="openai@gpt-4o-mini",
            message="hi",
        )
