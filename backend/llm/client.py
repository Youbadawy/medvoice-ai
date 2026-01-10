"""
MedVoice AI - LLM Client
OpenRouter client for DeepSeek V3.2 and GPT-4o-mini fallback.
"""

import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from .prompts import SystemPrompts
from .function_calls import BOOKING_TOOLS

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM client using OpenRouter for model access.
    Primary: DeepSeek V3.2 (best value, enhanced tool-use)
    Fallback: GPT-4o-mini (better French, proven reliability)
    """

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        primary_model: str = "deepseek/deepseek-v3.2",
        fallback_model: str = "openai/gpt-4o-mini"
    ):
        self.api_key = api_key
        self.primary_model = primary_model
        self.fallback_model = fallback_model

        # Initialize OpenAI client configured for OpenRouter
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": "https://medvoice-ai.web.app",
                "X-Title": "MedVoice AI"
            }
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        language: str = "fr",
        use_tools: bool = True,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Send a chat completion request.

        Args:
            messages: Conversation history
            language: Current language ('fr' or 'en')
            use_tools: Whether to include function calling tools
            use_fallback: Whether to use fallback model

        Returns:
            Dict with 'content' and optionally 'tool_calls'
        """
        model = self.fallback_model if use_fallback else self.primary_model

        try:
            # Build request
            request_params = {
                "model": model,
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7,
            }

            # Add tools if enabled
            if use_tools:
                request_params["tools"] = BOOKING_TOOLS
                request_params["tool_choice"] = "auto"

            # Make request
            response = await self.client.chat.completions.create(**request_params)

            # Extract response
            choice = response.choices[0]
            message = choice.message

            result = {
                "content": message.content or "",
                "tool_calls": None,
                "model": model,
                "finish_reason": choice.finish_reason
            }

            # Check for tool calls
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]

            logger.debug(f"LLM response ({model}): {result['content'][:100]}...")
            return result

        except Exception as e:
            logger.error(f"LLM error with {model}: {e}")

            # Try fallback if not already using it
            if not use_fallback and model == self.primary_model:
                logger.info("Attempting fallback model...")
                return await self.chat(
                    messages=messages,
                    language=language,
                    use_tools=use_tools,
                    use_fallback=True
                )

            # Return error response
            return {
                "content": self._get_error_message(language),
                "tool_calls": None,
                "model": model,
                "error": str(e)
            }

    async def get_response(
        self,
        conversation_history: List[Dict[str, str]],
        system_prompt: str,
        language: str = "fr"
    ) -> str:
        """
        Get a conversational response.

        Args:
            conversation_history: List of message dicts
            system_prompt: System prompt to use
            language: Current language

        Returns:
            Assistant response text
        """
        # Build messages with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)

        # Get response
        result = await self.chat(messages, language=language)

        # Handle tool calls if present
        if result.get("tool_calls"):
            # For now, just acknowledge tool calls
            # Full implementation would execute the tools
            tool_call = result["tool_calls"][0]
            logger.info(f"Tool call: {tool_call['function']['name']}")

        return result.get("content", "")

    def _get_error_message(self, language: str) -> str:
        """Get error message in the appropriate language."""
        if language == "fr":
            return "Je suis désolé, j'ai un petit problème technique. Pouvez-vous répéter s'il vous plaît?"
        else:
            return "I'm sorry, I'm having a small technical issue. Could you please repeat that?"


class ConversationContext:
    """Manages conversation context and history."""

    def __init__(self, language: str = "fr"):
        self.language = language
        self.messages: List[Dict[str, str]] = []
        self.extracted_slots: Dict[str, Any] = {}

    def add_user_message(self, content: str):
        """Add a user message to history."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str):
        """Add an assistant message to history."""
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_call_id: str, result: str):
        """Add a tool result to history."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result
        })

    def update_slot(self, slot_name: str, value: Any):
        """Update an extracted slot value."""
        self.extracted_slots[slot_name] = value

    def get_slot(self, slot_name: str) -> Optional[Any]:
        """Get an extracted slot value."""
        return self.extracted_slots.get(slot_name)

    def clear(self):
        """Clear conversation history."""
        self.messages = []
        self.extracted_slots = {}
