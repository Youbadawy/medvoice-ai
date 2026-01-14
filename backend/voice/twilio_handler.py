"""
MedVoice AI - Twilio Media Stream Handler
Handles bidirectional audio streaming with Twilio Voice.
"""

import json
import asyncio
import logging
import base64
from typing import Optional, AsyncIterator
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
        self.is_generating_response = False  # Guard against double responses
        self.audio_queue: asyncio.Queue = asyncio.Queue()
        self.should_stop = False

        # Media buffer synchronization lock
        self._media_lock = asyncio.Lock()
        self._asr_ready = False  # True only after ASR connected AND buffer flushed

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

        # Get custom parameters - log everything for debugging
        custom_params = start_data.get("customParameters", {})
        logger.info(f"📋 Custom parameters received: {custom_params}")
        logger.info(f"📋 Full start data: {start_data}")

        self.caller_number = custom_params.get("caller", "unknown")

        logger.info(f"📞 Stream started - SID: {self.stream_sid}, CallSID: {self.call_sid}, Caller: {self.caller_number}")

        # Initialize ASR client
        self.asr_client = DeepgramASRClient(
            api_key=self.settings.deepgram_api_key,
            on_transcript=self._on_transcript,
            on_utterance_end=self._on_utterance_end,
            on_speech_started=self._on_speech_started
        )
        self.media_buffer = []

        # Initialize TTS client
        self.tts_client = GoogleTTSClient(voice_gender=self.settings.voice_gender)

        # Initialize conversation manager
        self.conversation = ConversationManager(
            settings=self.settings,
            call_sid=self.call_sid,
            caller_number=self.caller_number
        )

        # START CONNECTION ASYNC - DO NOT BLOCK LOOP
        asyncio.create_task(self._connect_asr_and_flush())
        
        # Send greeting in background
        asyncio.create_task(self._send_greeting())

    async def _connect_asr_and_flush(self):
        """Connect to ASR and flush buffered media."""
        if not self.asr_client:
            return

        success = await self.asr_client.connect()
        if success:
            # Use lock to atomically flush buffer and set ready flag
            async with self._media_lock:
                logger.info(f"🚀 ASR Connected. Flushing {len(self.media_buffer)} buffered packets.")
                for payload in self.media_buffer:
                    try:
                        audio_data = base64.b64decode(payload)
                        await self.asr_client.send_audio(audio_data)
                    except Exception as e:
                        logger.error(f"Error flushing audio: {e}")
                self.media_buffer = []
                # Only set ready AFTER buffer is fully flushed
                self._asr_ready = True
                logger.info("✅ ASR ready for live audio")
        else:
            logger.error("❌ ASR Connection failed")

    async def _handle_media(self, data: dict):
        """Handle incoming audio from Twilio."""
        media = data.get("media", {})
        payload = media.get("payload")

        if not payload:
            return

        # Use lock to ensure atomic check-and-send/buffer
        async with self._media_lock:
            # Only send directly if ASR is fully ready (connected AND buffer flushed)
            if self._asr_ready and self.asr_client:
                try:
                    audio_data = base64.b64decode(payload)
                    await self.asr_client.send_audio(audio_data)
                except Exception as e:
                    logger.error(f"Error processing audio: {e}")
            else:
                # Buffer audio if not yet ready
                # Limit buffer size to avoid memory issues (e.g., 10 seconds of audio)
                if len(self.media_buffer) < 500:  # ~10s of 20ms packets
                    self.media_buffer.append(payload)

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

    async def _on_speech_started(self):
        """Callback when user starts speaking (Barge-in)."""
        # CHANGED: Do NOT stop audio immediately on sound detection.
        # Wait for actual transcript to avoid cutting off on noise.
        logger.info("🗣️ Speech started detected (Deepgram) - listening...")

    async def _stop_audio(self):
        """Stop current audio playback and clear queue."""
        if not self.is_playing_audio:
            return

        logger.info("🛑 Interrupting audio playback")
        self.is_playing_audio = False
        
        # Clear python queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
        # Send Clear message to Twilio to stop playback immediately
        if self.stream_sid:
            clear_message = {
                "event": "clear",
                "streamSid": self.stream_sid
            }
            await self.websocket.send_json(clear_message)

    async def _on_transcript(self, text: str, is_final: bool, language: str):
        """Callback when ASR produces a transcript."""
        if not text.strip():
            return

        # NEW: Interrupt only when we get actual text
        if self.is_playing_audio:
            logger.info(f"🛑 Interruption trigger: '{text}'")
            await self._stop_audio()

        if is_final:
            logger.info(f"🎤 Caller ({language}): {text}")

            if self.conversation:
                # Update detected language
                self.conversation.update_language(language)

                # Add to transcript
                await self.conversation.add_caller_message(text)

    async def _on_utterance_end(self):
        """Callback when ASR detects end of utterance."""
        # Guard against double responses - don't start new generation if one is in progress
        if self.is_generating_response:
            logger.info("⚠️ Utterance end ignored - already generating response")
            return

        if self.conversation:
            logger.info("⚡ Utterance end - generating response")

            # Get AI response
            # Use streaming for lower latency
            await self._speak_streaming()

    async def _send_greeting(self):
        """Send initial greeting based on default language."""
        if self.conversation:
            # OPTIMIZATION: Small delay to ensure Twilio stream is ready
            # This fixes the "silent greeting" issue where early audio is lost
            await asyncio.sleep(0.5)
            
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

                # Track TTS characters for cost calculation
                if self.conversation:
                    self.conversation.total_tts_chars += len(text)
                    await self.conversation.add_assistant_message(text)

        except Exception as e:
            logger.error(f"TTS error: {e}")

    async def _speak_streaming(self):
        """
        Stream AI response to TTS for minimal latency.
        Buffers tokens until sentence boundary, then speaks each chunk.
        """
        if not self.conversation:
            return

        # Set flag to prevent concurrent generations
        self.is_generating_response = True
        logger.info("🎯 Starting response generation")

        # Get detected language
        language = "fr-CA" if self.conversation.language == "fr" else "en-CA"

        # Sentence delimiters for chunking
        sentence_delimiters = ".!?,"
        buffer = ""
        full_response = ""

        try:
            # Stream tokens from LLM
            async for token in self.conversation.get_response_streaming():
                buffer += token
                full_response += token

                # Speak when we hit a sentence boundary and have enough text
                if any(d in token for d in sentence_delimiters) and len(buffer) > 20:
                    chunk = buffer.strip()
                    if chunk:
                        logger.info(f"🔊 Assistant (chunk): {chunk}")
                        await self._speak_chunk(chunk, language)
                    buffer = ""

            # Speak remaining text
            if buffer.strip():
                logger.info(f"🔊 Assistant (final): {buffer.strip()}")
                await self._speak_chunk(buffer.strip(), language)

            # Add full response to transcript
            if full_response and self.conversation:
                await self.conversation.add_assistant_message(full_response)

        except Exception as e:
            logger.error(f"Streaming TTS error: {e}")
        finally:
            # Always clear the flag when done
            self.is_generating_response = False
            logger.info("✅ Response generation complete")
            
    async def _speak_chunk(self, text: str, language: str):
        """Speak a single chunk of text."""
        if not text or not self.tts_client:
            return

        try:
            # Generate TTS
            audio_data = await self.tts_client.synthesize(text, language)

            if audio_data:
                mulaw_base64 = self.audio_converter.to_twilio_format(audio_data)

                # If valid audio, queue it
                if mulaw_base64:
                    await self.audio_queue.put(mulaw_base64)

                    # Track TTS characters for cost calculation
                    if self.conversation:
                        self.conversation.total_tts_chars += len(text)

        except Exception as e:
            logger.error(f"TTS chunk error: {e}")






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
