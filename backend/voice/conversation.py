"""
MedVoice AI - Conversation Manager
State machine for managing voice conversations.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from llm.client import LLMClient
from llm.prompts import SystemPrompts
from llm.function_calls import format_slots_for_speech, format_booking_confirmation

logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """States in the conversation flow."""
    GREETING = "greeting"
    LISTENING = "listening"
    PROCESSING = "processing"
    BOOKING_INTENT = "booking_intent"
    COLLECTING_VISIT_TYPE = "collecting_visit_type"
    SHOWING_SLOTS = "showing_slots"
    COLLECTING_SLOT_CHOICE = "collecting_slot_choice"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_PHONE = "collecting_phone"
    CONFIRMING_BOOKING = "confirming_booking"
    FAQ = "faq"
    TRANSFERRING = "transferring"
    ENDING = "ending"


class ConversationManager:
    """
    Manages the conversation state and flow.
    Coordinates between ASR, LLM, and TTS components.
    """

    # Emergency keywords that trigger immediate transfer
    EMERGENCY_KEYWORDS_FR = [
        "douleur thoracique", "mal au coeur", "douleur poitrine",
        "difficulté à respirer", "ne peut pas respirer", "étouffe",
        "saignement", "hémorragie", "perte de conscience", "évanoui",
        "urgence", "911", "ambulance"
    ]

    EMERGENCY_KEYWORDS_EN = [
        "chest pain", "heart attack", "can't breathe", "difficulty breathing",
        "choking", "bleeding", "hemorrhage", "unconscious", "passed out",
        "emergency", "911", "ambulance"
    ]

    def __init__(self, settings, call_sid: str, caller_number: str):
        self.settings = settings
        self.call_sid = call_sid
        self.caller_number = caller_number

        # State
        self.state = ConversationState.GREETING
        self.language = settings.default_language  # Default to French
        self.language_locked = False

        # LLM client
        self.llm_client = LLMClient(
            api_key=settings.openrouter_api_key,
            primary_model=settings.openrouter_model_primary,
            fallback_model=settings.openrouter_model_fallback
        )

        # Conversation history
        self.messages: List[Dict[str, str]] = []
        self.transcript: List[Dict[str, Any]] = []

        # Booking slots (extracted during conversation)
        self.slots: Dict[str, Any] = {
            "visit_type": None,
            "selected_slot": None,
            "patient_name": None,
            "patient_phone": None
        }

        # Available slots from calendar
        self.available_slots: List[Dict] = []

        logger.info(f"Conversation started: {call_sid}")

    def update_language(self, detected_language: str):
        """Update the conversation language if not locked."""
        if not self.language_locked and detected_language != self.language:
            self.language = detected_language
            logger.info(f"Language updated to: {detected_language}")

    def get_greeting(self) -> str:
        """Get the initial greeting in the appropriate language."""
        return SystemPrompts.get_greeting(self.language)

    async def add_caller_message(self, text: str):
        """Add a caller message to the transcript."""
        self.transcript.append({
            "speaker": "caller",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
            "language": self.language
        })

        # Add to LLM message history
        self.messages.append({"role": "user", "content": text})

    async def add_assistant_message(self, text: str):
        """Add an assistant message to the transcript."""
        self.transcript.append({
            "speaker": "assistant",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
            "language": self.language
        })

        # Add to LLM message history
        self.messages.append({"role": "assistant", "content": text})

    async def get_response(self) -> Optional[str]:
        """
        Get the AI response based on current state and last message.

        Returns:
            Response text to speak, or None if no response needed
        """
        if not self.messages:
            return None

        last_message = self.messages[-1].get("content", "").lower()

        # Check for emergency keywords
        if self._is_emergency(last_message):
            return SystemPrompts.get_emergency_message(self.language)

        # Check for transfer request
        if self._wants_transfer(last_message):
            self.state = ConversationState.TRANSFERRING
            return SystemPrompts.get_transfer_message(self.language)

        # Get LLM response
        try:
            system_prompt = SystemPrompts.get_prompt(self.language)
            response = await self.llm_client.get_response(
                conversation_history=self.messages,
                system_prompt=system_prompt,
                language=self.language
            )

            return response

        except Exception as e:
            logger.error(f"Error getting response: {e}")
            return self._get_error_response()

    def _is_emergency(self, text: str) -> bool:
        """Check if the message contains emergency keywords."""
        keywords = (
            self.EMERGENCY_KEYWORDS_FR if self.language == "fr"
            else self.EMERGENCY_KEYWORDS_EN
        )
        return any(keyword in text for keyword in keywords)

    def _wants_transfer(self, text: str) -> bool:
        """Check if the caller wants to speak to a human."""
        transfer_phrases_fr = [
            "parler à quelqu'un", "parler à une personne", "parler à un humain",
            "une vraie personne", "réceptionniste", "quelqu'un d'autre"
        ]
        transfer_phrases_en = [
            "speak to someone", "speak to a person", "speak to a human",
            "real person", "receptionist", "someone else", "talk to a human"
        ]

        phrases = transfer_phrases_fr if self.language == "fr" else transfer_phrases_en
        return any(phrase in text for phrase in phrases)

    def _get_error_response(self) -> str:
        """Get error response in the appropriate language."""
        if self.language == "fr":
            return "Je suis désolé, j'ai un petit problème. Pouvez-vous répéter?"
        else:
            return "I'm sorry, I'm having a small issue. Could you please repeat that?"

    async def handle_tool_call(self, tool_name: str, arguments: Dict) -> str:
        """
        Handle a tool call from the LLM.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Response text after tool execution
        """
        logger.info(f"Handling tool call: {tool_name}")

        if tool_name == "get_available_slots":
            return await self._handle_get_slots(arguments)

        elif tool_name == "book_appointment":
            return await self._handle_book_appointment(arguments)

        elif tool_name == "transfer_to_human":
            self.state = ConversationState.TRANSFERRING
            return SystemPrompts.get_transfer_message(self.language)

        elif tool_name == "cancel_appointment":
            return await self._handle_cancel_appointment(arguments)

        else:
            logger.warning(f"Unknown tool: {tool_name}")
            return self._get_error_response()

    async def _handle_get_slots(self, arguments: Dict) -> str:
        """Handle get_available_slots tool call."""
        # TODO: Call n8n webhook to get actual slots
        # For now, return mock data
        mock_slots = [
            {"slot_id": "1", "datetime": "2024-01-15T10:00:00", "formatted_datetime": "mardi le 15 janvier à 10h"},
            {"slot_id": "2", "datetime": "2024-01-15T14:30:00", "formatted_datetime": "mardi le 15 janvier à 14h30"},
            {"slot_id": "3", "datetime": "2024-01-16T09:00:00", "formatted_datetime": "mercredi le 16 janvier à 9h"},
        ]

        self.available_slots = mock_slots
        self.state = ConversationState.SHOWING_SLOTS

        return format_slots_for_speech(mock_slots, self.language)

    async def _handle_book_appointment(self, arguments: Dict) -> str:
        """Handle book_appointment tool call."""
        # TODO: Call n8n webhook to create booking
        # For now, return mock confirmation
        mock_booking = {
            "confirmation_number": "SL-2024-1234",
            "formatted_datetime": arguments.get("formatted_datetime", "mardi le 15 janvier à 10h"),
            "patient_name": arguments.get("patient_name", "")
        }

        self.state = ConversationState.ENDING

        return format_booking_confirmation(mock_booking, self.language)

    async def _handle_cancel_appointment(self, arguments: Dict) -> str:
        """Handle cancel_appointment tool call."""
        # TODO: Call n8n webhook to cancel
        if self.language == "fr":
            return "Votre rendez-vous a été annulé. Y a-t-il autre chose que je peux faire pour vous?"
        else:
            return "Your appointment has been cancelled. Is there anything else I can help you with?"

    async def save_transcript(self):
        """Save the conversation transcript to Firestore."""
        # TODO: Implement Firestore save
        logger.info(f"Saving transcript for call {self.call_sid}")
        logger.debug(f"Transcript: {json.dumps(self.transcript, indent=2)}")

    def get_transcript(self) -> List[Dict[str, Any]]:
        """Get the conversation transcript."""
        return self.transcript
