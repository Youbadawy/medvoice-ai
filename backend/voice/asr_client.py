"""
MedVoice AI - Deepgram ASR Client
Streaming speech-to-text with language detection.
Compatible with Deepgram SDK v5.
"""

import asyncio
import logging
from typing import Callable, Optional
from deepgram import DeepgramClient
from deepgram.listen import ListenV1Results, ListenV1UtteranceEnd

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
        on_utterance_end: Callable[[], None]
    ):
        self.api_key = api_key
        self.on_transcript = on_transcript
        self.on_utterance_end = on_utterance_end

        self.client: Optional[DeepgramClient] = None
        self.connection = None
        self.detected_language = "fr"  # Default to French for Quebec

        # Language detection state
        self.utterance_count = 0
        self.language_locked = False

    async def connect(self):
        """Establish connection to Deepgram."""
        try:
            self.client = DeepgramClient(api_key=self.api_key)

            # Configure for multilingual support
            options = {
                "model": "nova-2",
                "language": "multi",  # Auto-detect language
                "encoding": "mulaw",
                "sample_rate": 8000,
                "channels": 1,
                "interim_results": True,
                "utterance_end_ms": 1000,  # 1 second silence = end of utterance
                "vad_events": True,
                "endpointing": 300,  # 300ms for faster response
            }

            # Create WebSocket connection for live transcription
            self.connection = await self.client.listen.v1.connect(
                options=options,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            logger.info("🎙️ Deepgram ASR connected")
            return True

        except Exception as e:
            logger.error(f"Deepgram connection error: {e}")
            return False

    async def send_audio(self, audio_data: bytes):
        """Send audio data to Deepgram for transcription."""
        if self.connection:
            try:
                await self.connection.send(audio_data)
            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {e}")

    async def close(self):
        """Close the Deepgram connection."""
        if self.connection:
            try:
                await self.connection.finish()
                logger.info("🎙️ Deepgram connection closed")
            except Exception as e:
                logger.error(f"Error closing Deepgram: {e}")

    def _on_open(self, *args, **kwargs):
        """Handle connection open event."""
        logger.debug("Deepgram connection opened")

    async def _on_message(self, result, *args, **kwargs):
        """Handle message event from Deepgram."""
        try:
            # Check if it's a transcript result
            if isinstance(result, ListenV1Results):
                await self._handle_transcript(result)
            elif isinstance(result, ListenV1UtteranceEnd):
                await self._handle_utterance_end()
            else:
                # Try to handle as dict for backwards compatibility
                if hasattr(result, 'channel'):
                    await self._handle_transcript(result)
        except Exception as e:
            logger.error(f"Message processing error: {e}")

    async def _handle_transcript(self, result):
        """Process transcript result."""
        try:
            # Get channel data
            channel = result.channel if hasattr(result, 'channel') else None
            if not channel:
                return

            alternatives = channel.alternatives if hasattr(channel, 'alternatives') else []
            if not alternatives:
                return

            alternative = alternatives[0]
            transcript = alternative.transcript if hasattr(alternative, 'transcript') else ""

            if not transcript:
                return

            # Detect language from transcript
            detected_lang = self._detect_language(transcript)

            # Check if this is a final result
            is_final = result.is_final if hasattr(result, 'is_final') else True

            # Update language detection
            if is_final and not self.language_locked:
                self._update_language(detected_lang)

            # Call the transcript callback
            if self.on_transcript:
                await self.on_transcript(transcript, is_final, self.detected_language)

        except Exception as e:
            logger.error(f"Transcript processing error: {e}")

    async def _handle_utterance_end(self):
        """Handle utterance end event."""
        logger.debug("Utterance end detected")
        if self.on_utterance_end:
            await self.on_utterance_end()

    def _on_error(self, error, *args, **kwargs):
        """Handle error event."""
        logger.error(f"Deepgram error: {error}")

    def _on_close(self, *args, **kwargs):
        """Handle connection close event."""
        logger.debug("Deepgram connection closed")

    def _detect_language(self, transcript: str) -> str:
        """
        Detect language from transcript content.
        Returns 'fr' or 'en'.
        """
        # Detect from common French words/patterns
        french_indicators = [
            'bonjour', 'merci', 'oui', 'non', 'je', 'vous', 'rendez-vous',
            'docteur', "s'il vous plaît", 'clinique', 'santé', 'médecin',
            'disponible', 'quand', "aujourd'hui", 'demain', 'semaine',
            'voudrais', 'pouvez', 'avez', 'est-ce', 'comment', 'pourquoi'
        ]

        transcript_lower = transcript.lower()
        french_matches = sum(1 for word in french_indicators if word in transcript_lower)

        return 'fr' if french_matches > 0 else 'en'

    def _update_language(self, detected_lang: str):
        """Update the detected language, with lock after confidence."""
        self.utterance_count += 1

        # Lock language after 2 utterances to prevent flip-flopping
        if self.utterance_count >= 2:
            self.language_locked = True
            logger.info(f"🌐 Language locked to: {detected_lang}")
        else:
            self.detected_language = detected_lang
            logger.debug(f"🌐 Detected language: {detected_lang}")
