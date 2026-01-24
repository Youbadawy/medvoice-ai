"""
MedVoice AI - Conversation Manager
State machine for managing voice conversations.
Supports both traditional turn-based and PersonaPlex full-duplex modes.
"""

import logging
import json
import asyncio
from typing import Optional, List, Dict, Any, AsyncIterator, Callable
from datetime import datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from llm.client import LLMClient
from llm.prompts import SystemPrompts
from llm.function_calls import format_slots_for_speech, format_booking_confirmation
from storage.firebase_client import get_firebase_client
from services.booking import get_booking_service

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


class ConversationMode(Enum):
    """Conversation mode - traditional turn-based or PersonaPlex full-duplex."""
    TURN_BASED = "turn_based"
    FULL_DUPLEX = "full_duplex"


class ConversationManager:
    """
    Manages the conversation state and flow.
    Coordinates between ASR, LLM, and TTS components.

    Supports two modes:
    1. Turn-based (legacy): ASR -> LLM -> TTS pipeline
    2. Full-duplex (PersonaPlex): Continuous bidirectional audio/text streaming
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

        # Determine conversation mode
        self.mode = (
            ConversationMode.FULL_DUPLEX
            if settings.personaplex_enabled and settings.personaplex_api_key
            else ConversationMode.TURN_BASED
        )

        # Initialize appropriate client based on mode
        if self.mode == ConversationMode.FULL_DUPLEX:
            self._init_personaplex_client()
        else:
            self._init_turn_based_client()

        # Conversation history (used for both modes)
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

        # Firebase client
        self.firebase = get_firebase_client(settings.firebase_project_id)

        # Booking service (uses Firestore)
        self.booking_service = get_booking_service(self.firebase)

        # Track booking status
        self.booking_made = False
        self.start_time = datetime.utcnow()

        # Track conversation metrics for status determination
        self.ai_response_count = 0
        self.caller_message_count = 0

        # Usage metrics for cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tts_chars = 0

        # Prevent duplicate filler phrases during tool call chains
        self._filler_used_this_turn = False

        # Full-duplex specific state
        self._duplex_session_active = False
        self._emergency_triggered = False
        self._audio_push_task: Optional[asyncio.Task] = None
        self._event_loop_task: Optional[asyncio.Task] = None

        logger.info(f"Conversation started: {call_sid} (mode: {self.mode.value})")

        # Create call record in Firestore
        self._create_call_record()

    def _init_turn_based_client(self):
        """Initialize the traditional turn-based LLM client."""
        self.llm_client = LLMClient(
            api_key=self.settings.groq_api_key,
            primary_model=self.settings.groq_model_primary,
            fallback_model=self.settings.groq_model_fallback
        )
        self.personaplex_client = None

    def _init_personaplex_client(self):
        """Initialize the PersonaPlex full-duplex client."""
        from llm.personaplex_client import (
            PersonaPlexClient,
            PersonaPlexConfig
        )

        # Build PersonaPlex config from settings
        config = PersonaPlexConfig(
            endpoint_url=self.settings.personaplex_endpoint,
            api_key=self.settings.personaplex_api_key,
            voice_id=self.settings.personaplex_voice_id,
            voice_embedding_path=self.settings.personaplex_voice_embedding_path,
            enable_backchannels=self.settings.personaplex_enable_backchannels,
            enable_interruptions=self.settings.personaplex_enable_interruptions,
            vad_threshold=self.settings.personaplex_vad_threshold,
            silence_timeout_ms=self.settings.personaplex_silence_timeout_ms,
            primary_language="fr-CA" if self.language == "fr" else "en-US",
            secondary_language="en-US" if self.language == "fr" else "fr-CA",
            auto_language_switch=True
        )

        self.personaplex_client = PersonaPlexClient(config)

        # Also keep turn-based client as fallback
        self.llm_client = LLMClient(
            api_key=self.settings.groq_api_key,
            primary_model=self.settings.groq_model_primary,
            fallback_model=self.settings.groq_model_fallback
        )

    def update_language(self, detected_language: str):
        """Update the conversation language dynamically."""
        if detected_language != self.language:
            self.language = detected_language
            logger.info(f"Language updated to: {detected_language}")

    def get_greeting(self) -> str:
        """Get the initial greeting in the appropriate language."""
        return SystemPrompts.get_greeting(self.language)

    # ==================== FULL-DUPLEX MODE (PersonaPlex) ====================

    async def start_duplex_session(
        self,
        on_audio_output: Callable[[bytes], None],
        on_agent_text: Optional[Callable[[str], None]] = None
    ) -> None:
        """
        Start a full-duplex PersonaPlex session.

        This replaces the traditional get_response() turn-based pattern.
        Audio flows continuously in both directions.

        Args:
            on_audio_output: Callback to handle agent audio chunks (play to user)
            on_agent_text: Optional callback for agent text (for logging/display)
        """
        if self.mode != ConversationMode.FULL_DUPLEX:
            raise RuntimeError("Full-duplex mode not enabled")

        if not self.personaplex_client:
            raise RuntimeError("PersonaPlex client not initialized")

        logger.info(f"Starting full-duplex session for call {self.call_sid}")

        # Build system prompt with current context
        current_time = datetime.now(ZoneInfo("America/Montreal"))
        system_prompt = SystemPrompts.get_prompt(
            language=self.language,
            emotion_level=self.settings.emotion_level,
            current_time=current_time
        )

        # Start PersonaPlex session
        await self.personaplex_client.start_session(
            system_prompt=system_prompt,
            tool_handler=self._personaplex_tool_handler,
            on_emergency=self._handle_emergency_callback
        )

        self._duplex_session_active = True

        # Start the event processing loop
        self._event_loop_task = asyncio.create_task(
            self._process_personaplex_events(on_audio_output, on_agent_text)
        )

        logger.info("Full-duplex session started")

    async def push_audio(self, audio_chunk: bytes) -> None:
        """
        Push audio from the user's microphone to PersonaPlex.

        This should be called continuously as audio is captured.

        Args:
            audio_chunk: Raw PCM audio bytes
        """
        if not self._duplex_session_active:
            logger.warning("Attempted to push audio without active duplex session")
            return

        # Check for emergency keywords in any partial transcript
        # (PersonaPlex handles this via events, but we add a safety layer)
        await self.personaplex_client.push_audio(audio_chunk)

    async def _process_personaplex_events(
        self,
        on_audio_output: Callable[[bytes], None],
        on_agent_text: Optional[Callable[[str], None]]
    ) -> None:
        """
        Process events from the PersonaPlex stream.

        This runs as a background task and handles:
        - Audio output (forwarded to playback)
        - Transcripts (logged to Firebase)
        - Tool calls (executed and results returned)
        - Emergency interruptions
        """
        from llm.personaplex_client import PersonaPlexEvent

        try:
            async for event in self.personaplex_client.events():
                if self._emergency_triggered:
                    # Stop processing if emergency was triggered
                    break

                if event.event_type == PersonaPlexEvent.AUDIO_CHUNK:
                    # Forward audio to playback callback
                    if on_audio_output:
                        on_audio_output(event.data)

                elif event.event_type == PersonaPlexEvent.TRANSCRIPT_FINAL:
                    # User finished speaking - log and check for emergencies
                    user_text = event.data.get("text", "")
                    await self._handle_user_transcript(user_text)

                elif event.event_type == PersonaPlexEvent.AGENT_TEXT:
                    # Agent text output
                    agent_text = event.data.get("text", "")
                    if agent_text.strip():
                        self.ai_response_count += 1
                        if on_agent_text:
                            on_agent_text(agent_text)

                elif event.event_type == PersonaPlexEvent.TOOL_CALL:
                    # Tool call was executed (handled by _personaplex_tool_handler)
                    logger.info(f"Tool call processed: {event.data.tool_name}")

                elif event.event_type == PersonaPlexEvent.TURN_END:
                    # Agent finished speaking - save accumulated transcript
                    await self._save_agent_turn()

                elif event.event_type == PersonaPlexEvent.INTERRUPTION:
                    logger.info("User interrupted agent")

                elif event.event_type == PersonaPlexEvent.ERROR:
                    logger.error(f"PersonaPlex error: {event.data}")
                    # Could fall back to turn-based mode here

        except asyncio.CancelledError:
            logger.info("Event processing cancelled")
        except Exception as e:
            logger.error(f"Error processing PersonaPlex events: {e}")

    async def _handle_user_transcript(self, text: str) -> None:
        """Handle a finalized user transcript from PersonaPlex."""
        self.caller_message_count += 1

        # Log to transcript
        entry = {
            "speaker": "caller",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
            "language": self.language
        }
        self.transcript.append(entry)
        self.messages.append({"role": "user", "content": text})

        # Save to Firebase
        await self._save_transcript_entry(entry)

        # Check for emergency keywords
        if self._is_emergency(text.lower()):
            await self._trigger_emergency_interrupt(text)

        # Check for transfer request
        if self._wants_transfer(text.lower()):
            self.state = ConversationState.TRANSFERRING
            # PersonaPlex will handle the response

    async def _save_agent_turn(self) -> None:
        """Save the agent's completed turn to transcript."""
        # Get accumulated transcript from PersonaPlex
        transcript_entries = self.personaplex_client.get_transcript()

        for entry in transcript_entries:
            if entry.get("speaker") == "agent" and entry not in self.transcript:
                self.transcript.append(entry)
                self.messages.append({
                    "role": "assistant",
                    "content": entry.get("text", "")
                })
                await self._save_transcript_entry(entry)

    async def _personaplex_tool_handler(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> str:
        """
        Handle tool calls from PersonaPlex.

        This is the bridge between PersonaPlex's tool detection and our
        existing tool execution logic.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result as string
        """
        logger.info(f"PersonaPlex tool call: {tool_name}")

        try:
            result = await self.handle_tool_call(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return json.dumps({"error": str(e)})

    def _handle_emergency_callback(self, emergency_text: str) -> None:
        """Callback when PersonaPlex detects emergency (or we trigger it)."""
        logger.warning(f"Emergency callback triggered: {emergency_text}")
        self._emergency_triggered = True

    async def _trigger_emergency_interrupt(self, detected_text: str) -> None:
        """
        Trigger emergency interrupt - stop agent and inject emergency message.

        This immediately interrupts any ongoing agent speech and injects
        the emergency message to be spoken.
        """
        logger.warning(f"Emergency detected: {detected_text}")
        self._emergency_triggered = True

        if self.personaplex_client and self._duplex_session_active:
            # Interrupt the agent
            await self.personaplex_client.trigger_emergency_interrupt(detected_text)

            # Inject the emergency message
            emergency_message = SystemPrompts.get_emergency_message(self.language)
            await self.personaplex_client.inject_text(emergency_message)

            # Log to transcript
            entry = {
                "speaker": "system",
                "text": f"EMERGENCY DETECTED: {detected_text}",
                "timestamp": datetime.utcnow().isoformat(),
                "emergency": True
            }
            self.transcript.append(entry)
            await self._save_transcript_entry(entry)

    async def end_duplex_session(self) -> Dict[str, Any]:
        """
        End the full-duplex session gracefully.

        Returns:
            Session summary with metrics
        """
        if not self._duplex_session_active:
            return {}

        logger.info(f"Ending full-duplex session for call {self.call_sid}")

        self._duplex_session_active = False

        # Cancel event loop task
        if self._event_loop_task:
            self._event_loop_task.cancel()
            try:
                await self._event_loop_task
            except asyncio.CancelledError:
                pass

        # End PersonaPlex session
        if self.personaplex_client:
            session_summary = await self.personaplex_client.end_session()

            # Merge any remaining transcript entries
            for entry in session_summary.get("transcript", []):
                if entry not in self.transcript:
                    self.transcript.append(entry)

        # Save final transcript
        await self.save_transcript()

        return {
            "mode": "full_duplex",
            "duration_seconds": int((datetime.utcnow() - self.start_time).total_seconds()),
            "emergency_triggered": self._emergency_triggered
        }

    # ==================== TURN-BASED MODE (Legacy) ====================

    async def add_caller_message(self, text: str):
        """Add a caller message to the transcript and save immediately."""
        self.caller_message_count += 1
        # Reset filler flag for new turn
        self._filler_used_this_turn = False

        entry = {
            "speaker": "caller",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
            "language": self.language
        }
        self.transcript.append(entry)

        # Add to LLM message history
        self.messages.append({"role": "user", "content": text})

        # Save immediately to Firebase for live updates
        await self._save_transcript_entry(entry)

    async def add_assistant_message(self, text: str):
        """Add an assistant message to the transcript and save immediately."""
        entry = {
            "speaker": "assistant",
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
            "language": self.language
        }
        self.transcript.append(entry)

        # Add to LLM message history
        self.messages.append({"role": "assistant", "content": text})

        # Save immediately to Firebase for live updates
        await self._save_transcript_entry(entry)

    async def _save_transcript_entry(self, entry: Dict):
        """Save a single transcript entry for real-time updates."""
        if self.firebase and self.firebase.is_connected:
            try:
                transcript_ref = self.firebase.db.collection("calls").document(self.call_sid).collection("transcript")
                doc_ref = transcript_ref.document(f"{len(self.transcript)-1:04d}")
                doc_ref.set(entry)
            except Exception as e:
                logger.error(f"Error saving transcript entry: {e}")

    async def get_response(self) -> Optional[str]:
        """
        Get the AI response based on current state and last message.
        (Turn-based mode only)

        Returns:
            Response text to speak, or None if no response needed
        """
        if self.mode == ConversationMode.FULL_DUPLEX:
            logger.warning("get_response() called in full-duplex mode - use start_duplex_session() instead")
            return None

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

        try:
            # Inject emotion level and current time into system prompt
            current_time = datetime.now(ZoneInfo("America/Montreal"))
            system_prompt = SystemPrompts.get_prompt(
                language=self.language,
                emotion_level=self.settings.emotion_level,
                current_time=current_time
            )
            response_data = await self.llm_client.get_response(
                conversation_history=self.messages,
                system_prompt=system_prompt,
                language=self.language
            )

            # Track usage
            if response_data.get("usage"):
                self.total_input_tokens += response_data["usage"].get("input_tokens", 0)
                self.total_output_tokens += response_data["usage"].get("output_tokens", 0)

            response = response_data.get("content", "")

            if response:
                self.ai_response_count += 1

            return response

        except Exception as e:
            logger.error(f"Error getting response: {e}")
            return self._get_error_response()

    async def get_response_streaming(self) -> AsyncIterator[str]:
        """
        Get AI response with streaming for lower latency.
        (Turn-based mode - DEPRECATED in favor of full-duplex)

        Yields:
            String tokens as they arrive from LLM
        """
        if self.mode == ConversationMode.FULL_DUPLEX:
            logger.warning("get_response_streaming() is deprecated in full-duplex mode")
            return

        if not self.messages:
            return

        last_message = self.messages[-1].get("content", "").lower()

        # Check for emergency keywords - return full message immediately
        if self._is_emergency(last_message):
            yield SystemPrompts.get_emergency_message(self.language)
            return

        # Check for transfer request
        if self._wants_transfer(last_message):
            self.state = ConversationState.TRANSFERRING
            yield SystemPrompts.get_transfer_message(self.language)
            return

        # Stream LLM response
        try:
            # Inject emotion level and current time into system prompt
            current_time = datetime.now(ZoneInfo("America/Montreal"))
            system_prompt = SystemPrompts.get_prompt(
                language=self.language,
                emotion_level=self.settings.emotion_level,
                current_time=current_time
            )

            tool_calls_buffer = []

            async for chunk in self.llm_client.get_response_streaming(
                conversation_history=self.messages,
                system_prompt=system_prompt,
                language=self.language
            ):
                # Handle OpenAI chunk object
                if not hasattr(chunk, 'choices') or not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # 1. Handle Content
                if delta.content:
                    yield delta.content

                # 2. Handle Tool Calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        if len(tool_calls_buffer) <= tc.index:
                             tool_calls_buffer.append({"id": "", "function": {"name": "", "arguments": ""}})

                        existing = tool_calls_buffer[tc.index]

                        if tc.id:
                            existing["id"] = tc.id

                        if tc.function:
                            if tc.function.name:
                                existing["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                existing["function"]["arguments"] += tc.function.arguments

            self.ai_response_count += 1

            # Process tool calls if any
            if tool_calls_buffer:
                logger.info(f"🛠️ Processing {len(tool_calls_buffer)} tool calls from stream")

                # Yield filler phrase only once per turn to mask latency
                if not self._filler_used_this_turn:
                    filler = self._get_filler_phrase()
                    if filler:
                        self._filler_used_this_turn = True
                        yield filler

                for tool_call in tool_calls_buffer:
                    func_name = tool_call["function"]["name"]
                    func_args_str = tool_call["function"]["arguments"]

                    try:
                        func_args = json.loads(func_args_str)
                        logger.info(f"🛠️ Executing tool: {func_name} args: {func_args}")

                        # Execute tool
                        tool_result = await self.handle_tool_call(func_name, func_args)

                        # Add tool interaction to history
                        self.messages.append({
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": tool_call["id"],
                                    "type": "function",
                                    "function": {
                                        "name": func_name,
                                        "arguments": func_args_str
                                    }
                                }
                            ]
                        })

                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result
                        })

                        # Recursively get new response (streaming)
                        async for token in self.get_response_streaming():
                            yield token

                    except json.JSONDecodeError:
                        logger.error(f"❌ Failed to parse arguments for tool {func_name}")
                    except Exception as e:
                        logger.error(f"❌ Error executing tool {func_name}: {e}")

        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield self._get_error_response()

    # ==================== SHARED FUNCTIONALITY ====================

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
        """Get error response in the appropriate language - warm and apologetic."""
        if self.language == "fr":
            return "Oups, pardon! J'ai manqué ça. Pouvez-vous me répéter s'il vous plaît?"
        else:
            return "Oops, sorry about that! I missed that. Could you say that again for me?"

    def _get_filler_phrase(self) -> str:
        """Get a natural filler phrase to mask latency during tool calls."""
        import random

        # More natural, conversational fillers that sound human
        fillers_fr = [
            "Parfait, je regarde ça pour vous.",
            "Super, laissez-moi vérifier nos disponibilités.",
            "Excellent, je consulte notre calendrier.",
            "Bien sûr, je vérifie ça tout de suite.",
            "D'accord, je regarde ce qu'on a de disponible.",
        ]

        fillers_en = [
            "Perfect, let me check that for you.",
            "Great, let me look at our availability.",
            "Absolutely, I'll check our calendar.",
            "Sure thing, let me see what we have.",
            "Of course, I'm checking our schedule now.",
        ]

        if self.language == "fr":
            return random.choice(fillers_fr)
        else:
            return random.choice(fillers_en)

    def get_call_status(self) -> str:
        """
        Determine the call outcome based on conversation metrics.

        Returns:
            'completed' - Successful interaction (AI responded)
            'failed' - Caller spoke but AI never responded
            'transferred' - Call was transferred to human
            'no_interaction' - No caller messages (immediate hangup)
        """
        if self.state == ConversationState.TRANSFERRING:
            return "transferred"

        # Failed if caller spoke but AI never responded
        if self.caller_message_count > 0 and self.ai_response_count == 0:
            return "failed"

        # No interaction if caller never spoke
        if self.caller_message_count == 0:
            return "no_interaction"

        return "completed"

    async def handle_tool_call(self, tool_name: str, arguments: Dict) -> str:
        """
        Handle a tool call from the LLM (works for both modes).

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
        visit_type = arguments.get("visit_type", "general")
        preferred_date = arguments.get("preferred_date")
        days_to_search = arguments.get("days_to_search", 7)

        # Get slots from booking service (n8n or mock)
        slots = await self.booking_service.get_available_slots(
            visit_type=visit_type,
            preferred_date=preferred_date,
            days_to_search=days_to_search,
            language=self.language
        )

        self.available_slots = slots
        self.slots["visit_type"] = visit_type
        self.state = ConversationState.SHOWING_SLOTS

        logger.info(f"Retrieved {len(slots)} available slots")

        return format_slots_for_speech(slots, self.language)

    async def _handle_book_appointment(self, arguments: Dict) -> str:
        """Handle book_appointment tool call."""
        slot_id = arguments.get("slot_id", "1")
        patient_name = arguments.get("patient_name", "")
        patient_phone = arguments.get("patient_phone", self.caller_number)
        visit_type = arguments.get("visit_type", self.slots.get("visit_type", "general"))
        ramq_number = arguments.get("ramq_number")
        consent_given = arguments.get("consent_given", False)
        notes = arguments.get("notes")

        # Basic RAMQ Validation (Client-side check)
        # RAMQ format: 4 letters + 8 digits (e.g. BADA 1234 5678)
        if ramq_number:
            import re
            # Remove spaces and hyphens
            clean_ramq = re.sub(r'[\s-]', '', ramq_number).upper()
            if not re.match(r'^[A-Z]{4}\d{8}$', clean_ramq):
                 logger.warning(f"Invalid RAMQ format: {ramq_number}")

        # Get formatted datetime from available slots
        formatted_datetime = ""
        if self.available_slots:
            for slot in self.available_slots:
                if slot.get("slot_id") == slot_id:
                    formatted_datetime = slot.get("formatted_datetime", "")
                    break
            if not formatted_datetime and self.available_slots:
                formatted_datetime = self.available_slots[0].get("formatted_datetime", "")

        # Book via booking service (n8n or mock)
        booking = await self.booking_service.book_appointment(
            slot_id=slot_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            visit_type=visit_type,
            ramq_number=ramq_number,
            consent_given=consent_given,
            notes=notes,
            formatted_datetime=formatted_datetime,
            language=self.language
        )

        # Update slots with patient info
        self.slots["patient_name"] = patient_name
        self.slots["patient_phone"] = patient_phone
        self.slots["selected_slot"] = slot_id

        logger.info(f"Booking confirmed: {booking.get('confirmation_number')}")

        # Send SMS confirmation only if not already sent (prevent duplicates)
        if not self.booking_made:
            self.booking_made = True
            self.state = ConversationState.ENDING

            try:
                from services.notification import get_notification_service
                notification_service = get_notification_service()

                # Use formatted datetime if available
                appt_time_str = formatted_datetime or slot_id

                # Run in background to not block response
                asyncio.create_task(notification_service.send_booking_confirmation(
                    patient_phone=patient_phone,
                    patient_name=patient_name,
                    appointment_time=appt_time_str,
                    confirmation_code=booking.get('confirmation_number', ''),
                    language=self.language
                ))
                logger.info(f"SMS confirmation queued for {patient_phone}")
            except Exception as e:
                logger.error(f"Failed to queue SMS confirmation: {e}")
        else:
            logger.warning("SMS confirmation already sent - skipping duplicate")

        return format_booking_confirmation(booking, self.language)

    async def _handle_cancel_appointment(self, arguments: Dict) -> str:
        """Handle cancel_appointment tool call."""
        confirmation_number = arguments.get("confirmation_number", "")
        patient_phone = arguments.get("patient_phone", self.caller_number)
        reason = arguments.get("reason")

        result = await self.booking_service.cancel_appointment(
            confirmation_number=confirmation_number,
            patient_phone=patient_phone,
            reason=reason,
            language=self.language
        )

        if result.get("success"):
            if self.language == "fr":
                return f"Votre rendez-vous {confirmation_number} a été annulé. Y a-t-il autre chose que je peux faire pour vous?"
            else:
                return f"Your appointment {confirmation_number} has been cancelled. Is there anything else I can help you with?"
        else:
            if self.language == "fr":
                return "Je n'ai pas pu trouver ce rendez-vous. Pouvez-vous vérifier le numéro de confirmation?"
            else:
                return "I couldn't find that appointment. Could you please verify the confirmation number?"

    def _create_call_record(self):
        """Create initial call record in Firestore."""
        try:
            call_data = {
                "call_sid": self.call_sid,
                "caller_number": self.caller_number,
                "language": self.language,
                "status": "active",
                "started_at": self.start_time.isoformat(),
                "mode": self.mode.value  # Track conversation mode
            }
            # Run async in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.firebase.create_call(call_data))
            else:
                loop.run_until_complete(self.firebase.create_call(call_data))
            logger.info(f"Call record created: {self.call_sid}")
        except Exception as e:
            logger.error(f"Error creating call record: {e}")

    async def save_transcript(self):
        """Save the conversation transcript to Firestore."""
        try:
            # Calculate duration
            end_time = datetime.utcnow()
            duration_seconds = int((end_time - self.start_time).total_seconds())

            # Determine call status
            call_status = self.get_call_status()

            # Calculate Costs
            from services.cost_tracker import CostService

            # Estimate tokens from conversation history (streaming doesn't return usage)
            if self.total_input_tokens < 50 or self.total_output_tokens < 50:
                input_chars = 0
                output_chars = 0

                for msg in self.messages:
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        if msg.get("role") in ["user", "system"]:
                            input_chars += len(content)
                        elif msg.get("role") == "assistant":
                            output_chars += len(content)

                # Estimate: ~4 chars per token
                self.total_input_tokens = max(self.total_input_tokens, int(input_chars / 4))
                self.total_output_tokens = max(self.total_output_tokens, int(output_chars / 4))

                logger.info(f"Token estimation: input={self.total_input_tokens}, output={self.total_output_tokens}")

            cost_data = CostService.calculate_call_cost(
                duration_seconds=duration_seconds,
                tts_characters=self.total_tts_chars,
                llm_input_tokens=self.total_input_tokens,
                llm_output_tokens=self.total_output_tokens,
                model_name=self.settings.openrouter_model_primary
            )

            # Update call record
            await self.firebase.end_call(self.call_sid, {
                "status": call_status,
                "duration_seconds": duration_seconds,
                "booking_made": self.booking_made,
                "language": self.language,
                "ended_at": end_time.isoformat(),
                "ai_response_count": self.ai_response_count,
                "caller_message_count": self.caller_message_count,
                "mode": self.mode.value,
                "emergency_triggered": self._emergency_triggered,
                "cost_data": cost_data,
                "usage_metrics": {
                    "tts_chars": self.total_tts_chars,
                    "input_tokens": self.total_input_tokens,
                    "output_tokens": self.total_output_tokens
                }
            })

            # Save transcript
            await self.firebase.save_transcript(self.call_sid, self.transcript)

            logger.info(f"Transcript saved for call {self.call_sid}, status: {call_status}, cost: ${cost_data['total_cost']}")
        except Exception as e:
            logger.error(f"Error saving transcript: {e}")

    def get_transcript(self) -> List[Dict[str, Any]]:
        """Get the conversation transcript."""
        return self.transcript
