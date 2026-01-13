"""
MedVoice AI - Deepgram ASR Client
Streaming speech-to-text with language detection.
Compatible with Deepgram SDK v3.5+.
"""

import asyncio
import logging
import time
import threading
from collections import deque
from typing import Callable, Optional, Any
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

logger = logging.getLogger(__name__)


class DeepgramASRClient:
    """
    Deepgram streaming ASR client with bilingual support.
    Handles French-Canadian and English transcription.
    """

    def __init__(
        self,
        api_key: str,
        on_transcript: Callable[[str, bool, str], None],
        on_utterance_end: Callable[[], None],
        on_speech_started: Optional[Callable[[], None]] = None,
        silence_timeout: float = 2.5  # Increased for better listening (phone numbers)
    ):
        self.api_key = api_key
        self.on_transcript = on_transcript
        self.on_utterance_end = on_utterance_end
        self.on_speech_started = on_speech_started

        self.client: Optional[DeepgramClient] = None
        self.connection = None
        self._is_connected = False
        self.detected_language = "fr"  # Default to French for Quebec
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Language detection state
        # CHANGED: Removed language_locked to support bilingual switching
        self.utterance_count = 0

        # Silence timer fallback (for when UtteranceEnd doesn't fire)
        self._silence_timer: Optional[asyncio.TimerHandle] = None
        self._silence_timeout = silence_timeout
        self._has_pending_final = False

        # Connection ready event for synchronization
        self._connection_ready = asyncio.Event()

        # Callback queue for when event loop isn't ready yet
        self._callback_queue: deque = deque(maxlen=100)
        self._queue_lock = threading.Lock()

    async def connect(self):
        """Establish connection to Deepgram."""
        try:
            # Store the event loop for callbacks - get the running loop
            self._loop = asyncio.get_running_loop()
            logger.info(f"🎙️ Event loop captured: {self._loop}")

            self.client = DeepgramClient(self.api_key)

            # Configure for multilingual support
            options = LiveOptions(
                model="nova-2",
                language="multi",  # Auto-detect language
                encoding="mulaw",
                sample_rate=8000,
                channels=1,
                interim_results=True,
                vad_events=True,
                endpointing=3000,  # 3000ms to allow long pauses (prevent cutting off numbers)
                smart_format=True, # Improved number formatting (514-123-4567)
            )

            # Create WebSocket connection for live transcription
            self.connection = self.client.listen.live.v("1")

            # Register event handlers (must be synchronous)
            self.connection.on(LiveTranscriptionEvents.Open, self._on_open)
            self.connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript_event)
            self.connection.on(LiveTranscriptionEvents.UtteranceEnd, self._on_utterance_end_event)
            self.connection.on(LiveTranscriptionEvents.SpeechStarted, self._on_speech_started_event)
            self.connection.on(LiveTranscriptionEvents.Error, self._on_error)
            self.connection.on(LiveTranscriptionEvents.Close, self._on_close)

            # Start the connection (synchronous in SDK v3.5+)
            logger.info("🎙️ Starting Deepgram connection...")
            result = self.connection.start(options)

            if not result:
                logger.error("❌ Failed to start Deepgram connection")
                return False

            # Wait for connection ready event (set by _on_open callback)
            try:
                await asyncio.wait_for(self._connection_ready.wait(), timeout=5.0)
                logger.info("🎙️ Deepgram ASR connected and ready")

                # Process any queued callbacks now that loop is ready
                self._process_queued_callbacks()

                return True
            except asyncio.TimeoutError:
                logger.error("❌ Deepgram connection timeout waiting for Open event")
                return False

        except Exception as e:
            logger.error(f"❌ Deepgram connection error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram for transcription."""
        if self.connection:
            try:
                self.connection.send(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {e}")

    async def close(self):
        """Close the Deepgram connection."""
        # Cancel silence timer on cleanup
        self._cancel_silence_timer()

        if self.connection:
            try:
                self.connection.finish()
                logger.info("🎙️ Deepgram connection closed")
            except Exception as e:
                logger.error(f"Error closing Deepgram: {e}")

    def _on_open(self, *args, **kwargs):
        """Handle connection open event."""
        logger.info("🎙️ Deepgram connection opened")
        self._is_connected = True
        # Signal that connection is ready (thread-safe)
        if self._loop:
            self._loop.call_soon_threadsafe(self._connection_ready.set)

    def _on_transcript_event(self, *args, **kwargs):
        """Handle transcript event from Deepgram (sync callback)."""
        try:
            result = kwargs.get('result') or (args[1] if len(args) > 1 else None)
            if result is None:
                logger.debug("📝 Transcript event received but result is None")
                return

            # Quick preview of transcript for debugging
            try:
                channel = getattr(result, 'channel', None)
                if channel:
                    alts = getattr(channel, 'alternatives', [])
                    if alts:
                        text = getattr(alts[0], 'transcript', '')
                        is_final = getattr(result, 'is_final', False)
                        if text:
                            logger.info(f"📝 Transcript received: '{text}' (final={is_final})")
            except:
                pass

            # Schedule async work on the event loop
            self._schedule_callback('transcript', result)
        except Exception as e:
            logger.error(f"❌ Transcript event error: {e}")

    def _on_utterance_end_event(self, *args, **kwargs):
        """Handle utterance end event from Deepgram (sync callback)."""
        logger.info("🎤 Utterance end detected (Deepgram event)")

        # Cancel fallback timer since Deepgram fired the event
        self._cancel_silence_timer()
        self._has_pending_final = False

        if self.on_utterance_end:
            self._schedule_callback('utterance_end', None)

    def _on_speech_started_event(self, *args, **kwargs):
        """Handle speech started event from Deepgram (sync callback)."""
        logger.info("🗣️ Speech started detected")
        if self.on_speech_started:
            self._schedule_callback('speech_started', None)

    def _schedule_callback(self, callback_type: str, data: Any):
        """Schedule a callback on the event loop, or queue if not ready."""
        try:
            if self._loop and self._is_connected:
                # Event loop is ready, schedule directly
                if callback_type == 'transcript':
                    asyncio.run_coroutine_threadsafe(
                        self._handle_transcript(data),
                        self._loop
                    )
                elif callback_type == 'utterance_end':
                    asyncio.run_coroutine_threadsafe(
                        self.on_utterance_end(),
                        self._loop
                    )
                elif callback_type == 'speech_started':
                    asyncio.run_coroutine_threadsafe(
                        self.on_speech_started(),
                        self._loop
                    )
            else:
                # Queue callback for later processing
                logger.warning(f"⏳ Queuing {callback_type} callback (loop not ready)")
                with self._queue_lock:
                    self._callback_queue.append((callback_type, data))
        except Exception as e:
            logger.error(f"❌ Error scheduling callback: {e}")

    def _process_queued_callbacks(self):
        """Process any callbacks that were queued before loop was ready."""
        with self._queue_lock:
            queue_size = len(self._callback_queue)
            if queue_size > 0:
                logger.info(f"📋 Processing {queue_size} queued callbacks")

            while self._callback_queue:
                callback_type, data = self._callback_queue.popleft()
                try:
                    if callback_type == 'transcript' and data:
                        asyncio.run_coroutine_threadsafe(
                            self._handle_transcript(data),
                            self._loop
                        )
                    elif callback_type == 'utterance_end' and self.on_utterance_end:
                        asyncio.run_coroutine_threadsafe(
                            self.on_utterance_end(),
                            self._loop
                        )
                    elif callback_type == 'speech_started' and self.on_speech_started:
                        asyncio.run_coroutine_threadsafe(
                            self.on_speech_started(),
                            self._loop
                        )
                except Exception as e:
                    logger.error(f"❌ Error processing queued callback: {e}")

    def _reset_silence_timer(self):
        """Reset silence timer after final transcript."""
        if self._silence_timer and not self._silence_timer.cancelled():
            self._silence_timer.cancel()

        if self._loop and self._is_connected:
            self._silence_timer = self._loop.call_later(
                self._silence_timeout,
                self._on_silence_timeout
            )

    def _on_silence_timeout(self):
        """Fallback: trigger utterance end after silence timeout."""
        if self._has_pending_final:
            logger.info("🎤 Silence timeout - triggering response (fallback)")
            self._has_pending_final = False
            if self.on_utterance_end:
                self._schedule_callback('utterance_end', None)

    def _cancel_silence_timer(self):
        """Cancel the silence timer."""
        if self._silence_timer and not self._silence_timer.cancelled():
            self._silence_timer.cancel()
            self._silence_timer = None

    async def _handle_transcript(self, result: Any):
        """Process transcript result."""
        try:
            # Get channel data - SDK v3 structure
            channel = getattr(result, 'channel', None)
            if not channel:
                return

            alternatives = getattr(channel, 'alternatives', [])
            if not alternatives:
                return

            alternative = alternatives[0]
            transcript = getattr(alternative, 'transcript', "")

            if not transcript:
                return

            # Detect language from transcript
            detected_lang = self._detect_language(transcript)

            # Check if this is a final result
            is_final = getattr(result, 'is_final', True)

            # Update language detection
            # CHANGED: Allow fluid switching on every turn (no locking)
            if is_final:
                self._update_language(detected_lang)

            # Start silence timer on final transcript (fallback for UtteranceEnd)
            if is_final:
                self._has_pending_final = True
                self._reset_silence_timer()

            # Call the transcript callback
            if self.on_transcript:
                await self.on_transcript(transcript, is_final, self.detected_language)

        except Exception as e:
            logger.error(f"Transcript processing error: {e}")

    def _on_error(self, *args, **kwargs):
        """Handle error event."""
        error = kwargs.get('error') or (args[1] if len(args) > 1 else "Unknown error")
        logger.error(f"Deepgram error: {error}")

    def _on_close(self, *args, **kwargs):
        """Handle connection close event."""
        logger.info("🎙️ Deepgram connection closed event")

    def _detect_language(self, transcript: str) -> str:
        """
        Detect language from transcript content.
        Returns 'fr' or 'en'.
        """
        french_indicators = [
            'bonjour', 'merci', 'oui', 'non', 'je', 'vous', 'rendez-vous',
            'docteur', "s'il vous plaît", 'clinique', 'santé', 'médecin',
            'disponible', 'quand', "aujourd'hui", 'demain', 'semaine',
            'voudrais', 'pouvez', 'avez', 'est-ce', 'comment', 'pourquoi',
            'salut', 'allo', 'allô', 'bien', 'mal', 'ça', 'c\'est',
            'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix'
        ]

        transcript_lower = transcript.lower()
        french_matches = sum(1 for word in french_indicators if word in transcript_lower)

        return 'fr' if french_matches > 0 else 'en'

    def _update_language(self, detected_lang: str):
        """Update the detected language immediately (fluid switching)."""
        if self.detected_language != detected_lang:
            self.detected_language = detected_lang
            logger.info(f"🌐 Language switched to: {detected_lang}")
