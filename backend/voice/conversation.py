"""
MedVoice AI - Conversation Manager
State machine for managing voice conversations.
"""

import logging
import json
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime, timedelta
from enum import Enum

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

        logger.info(f"Conversation started: {call_sid}")

        # Create call record in Firestore
        self._create_call_record()

    def update_language(self, detected_language: str):
        """Update the conversation language dynamically."""
        if detected_language != self.language:
            self.language = detected_language
            logger.info(f"Language updated to: {detected_language}")

    def get_greeting(self) -> str:
        """Get the initial greeting in the appropriate language."""
        return SystemPrompts.get_greeting(self.language)

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

        try:
            # Inject emotion level into system prompt
            system_prompt = SystemPrompts.get_prompt(
                language=self.language,
                emotion_level=self.settings.emotion_level
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

        Yields:
            String tokens as they arrive from LLM
        """
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
        # Stream LLM response
        try:
            # Inject emotion level into system prompt
            system_prompt = SystemPrompts.get_prompt(
                language=self.language,
                emotion_level=self.settings.emotion_level
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
                        # The system prompt is regenerated in the next call, so it will pick up the settings.
                        # We yield the result of the new stream
                        async for token in self.get_response_streaming():
                            yield token
                            
                    except json.JSONDecodeError:
                        logger.error(f"❌ Failed to parse arguments for tool {func_name}")
                    except Exception as e:
                        logger.error(f"❌ Error executing tool {func_name}: {e}")

        except Exception as e:
            logger.error(f"Error streaming response: {e}")
            yield self._get_error_response()

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
                 # You might want to ask the user to repeat, but for MVP we log it.
                 # In a real system, we'd return a tool error or ask again.

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

                # Use formatted datetime if available, otherwise raw slot ID (not ideal but fallback)
                appt_time_str = formatted_datetime or slot_id

                # Run in background to not block response
                import asyncio
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
            import asyncio
            call_data = {
                "call_sid": self.call_sid,
                "caller_number": self.caller_number,
                "language": self.language,
                "status": "active",
                "started_at": self.start_time.isoformat()
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
            # Rough est: 1 token ~= 4 chars of text
            # Always estimate for streaming since OpenRouter streaming doesn't return usage
            if self.total_input_tokens < 50 or self.total_output_tokens < 50:
                # Use full messages array for more accurate estimation
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
                "cost_data": cost_data,  # Save cost data
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
