"""
MedVoice AI - Twilio Media Stream Handler
Handles bidirectional audio streaming with Twilio Voice.
"""

import json
import asyncio
import logging
import base64
from typing import Optional
from fastapi import WebSocket

from .asr_client import DeepgramASRClient
from .tts_client import GoogleTTSClient
from .audio_utils import AudioConverter
from .conversation import ConversationManager

logger = logging.getLogger(__name__)


class TwilioMediaStreamHandler:
    """
    Handles Twilio Media Stream WebSocket connections.
    Orchestrates ASR, LLM, and TTS for voice conversations.
    """

    def __init__(self, websocket: WebSocket, settings):
        self.websocket = websocket
        self.settings = settings

        # Stream identifiers
        self.stream_sid: Optional[str] = None
        self.call_sid: Optional[str] = None
        self.caller_number: Optional[str] = None

        # Audio components
        self.asr_client: Optional[DeepgramASRClient] = None
        self.tts_client: Optional[GoogleTTSClient] = None
        self.audio_converter = AudioConverter()

        # Conversation manager
        self.conversation: Optional[ConversationManager] = None

        # State
        self.is_playing_audio = False
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.should_stop = False

    async def handle_stream(self):
        """Main loop to handle incoming WebSocket messages from Twilio."""
        try:
            # Start audio sender task
            sender_task = asyncio.create_task(self._audio_sender())

            async for message in self.websocket.iter_text():
                if self.should_stop:
                    break

                data = json.loads(message)
                event_type = data.get("event")

                if event_type == "connected":
                    await self._handle_connected(data)

                elif event_type == "start":
                    await self._handle_start(data)

                elif event_type == "media":
                    await self._handle_media(data)

                elif event_type == "mark":
                    await self._handle_mark(data)

                elif event_type == "stop":
                    await self._handle_stop(data)
                    break

            sender_task.cancel()

        except Exception as e:
            logger.error(f"Stream handler error: {e}")
            raise

    async def _handle_connected(self, data: dict):
        """Handle stream connected event."""
        logger.info("🔗 Twilio stream connected")
        logger.debug(f"Connected data: {data}")

    async def _handle_start(self, data: dict):
        """Handle stream start event - initialize components."""
        start_data = data.get("start", {})
        self.stream_sid = start_data.get("streamSid")
        self.call_sid = start_data.get("callSid")

        # Get custom parameters
        custom_params = start_data.get("customParameters", {})
        self.caller_number = custom_params.get("caller", "unknown")

        logger.info(f"📞 Stream started - SID: {self.stream_sid}, Caller: {self.caller_number}")

        # Initialize ASR client
        self.asr_client = DeepgramASRClient(
            api_key=self.settings.deepgram_api_key,
            on_transcript=self._on_transcript,
            on_utterance_end=self._on_utterance_end
        )
        await self.asr_client.connect()

        # Initialize TTS client (uses GOOGLE_APPLICATION_CREDENTIALS)
        self.tts_client = GoogleTTSClient()

        # Initialize conversation manager
        self.conversation = ConversationManager(
            settings=self.settings,
            call_sid=self.call_sid,
            caller_number=self.caller_number
        )

        # Send initial greeting
        await self._send_greeting()

    async def _handle_media(self, data: dict):
        """Handle incoming audio from Twilio."""
        media = data.get("media", {})
        payload = media.get("payload")

        if payload and self.asr_client:
            # Decode base64 mulaw audio
            audio_data = base64.b64decode(payload)
            # Send to ASR
            await self.asr_client.send_audio(audio_data)

    async def _handle_mark(self, data: dict):
        """Handle mark event - audio playback acknowledgment."""
        mark_name = data.get("mark", {}).get("name")
        logger.debug(f"✓ Mark received: {mark_name}")

        if mark_name == "audio_end":
            self.is_playing_audio = False

    async def _handle_stop(self, data: dict):
        """Handle stream stop event."""
        logger.info("🛑 Stream stopped")
        self.should_stop = True

    async def _on_transcript(self, text: str, is_final: bool, language: str):
        """Callback when ASR produces a transcript."""
        if not text.strip():
            return

        if is_final:
            logger.info(f"🎤 Caller ({language}): {text}")

            if self.conversation:
                # Update detected language
                self.conversation.update_language(language)

                # Add to transcript
                await self.conversation.add_caller_message(text)

    async def _on_utterance_end(self):
        """Callback when ASR detects end of utterance."""
        if self.conversation and not self.is_playing_audio:
            # Get AI response
            response = await self.conversation.get_response()

            if response:
                # Synthesize and send audio
                await self._speak(response)

    async def _send_greeting(self):
        """Send initial greeting based on default language."""
        if self.conversation:
            greeting = self.conversation.get_greeting()
            await self._speak(greeting)

    async def _speak(self, text: str):
        """Convert text to speech and send to Twilio."""
        if not text or not self.tts_client:
            return

        logger.info(f"🔊 Assistant: {text}")

        # Get detected language from conversation
        language = "fr-CA" if self.conversation and self.conversation.language == "fr" else "en-CA"

        try:
            # Synthesize speech
            audio_data = await self.tts_client.synthesize(text, language)

            if audio_data:
                # Convert to Twilio format (mulaw base64)
                mulaw_base64 = self.audio_converter.to_twilio_format(audio_data)

                # Queue audio for sending
                await self.audio_queue.put(mulaw_base64)

                # Add to transcript
                if self.conversation:
                    await self.conversation.add_assistant_message(text)

        except Exception as e:
            logger.error(f"TTS error: {e}")

    async def _audio_sender(self):
        """Background task to send audio to Twilio."""
        while not self.should_stop:
            try:
                # Wait for audio in queue
                audio_base64 = await asyncio.wait_for(
                    self.audio_queue.get(),
                    timeout=0.1
                )

                if audio_base64 and self.stream_sid:
                    self.is_playing_audio = True

                    # Send audio to Twilio
                    message = {
                        "event": "media",
                        "streamSid": self.stream_sid,
                        "media": {
                            "payload": audio_base64
                        }
                    }
                    await self.websocket.send_json(message)

                    # Send mark to know when audio finishes
                    mark_message = {
                        "event": "mark",
                        "streamSid": self.stream_sid,
                        "mark": {
                            "name": "audio_end"
                        }
                    }
                    await self.websocket.send_json(mark_message)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if not self.should_stop:
                    logger.error(f"Audio sender error: {e}")
                break

    async def cleanup(self):
        """Clean up resources."""
        self.should_stop = True

        if self.asr_client:
            await self.asr_client.close()

        if self.conversation:
            await self.conversation.save_transcript()

        logger.info("🧹 Handler resources cleaned up")
