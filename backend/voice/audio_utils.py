"""
MedVoice AI - Audio Utilities
Audio format conversion for Twilio Media Streams.
"""

import base64
import logging
from typing import Optional

# audioop-lts provides audioop for Python 3.13+
try:
    import audioop
except ImportError:
    import audioop_lts as audioop

logger = logging.getLogger(__name__)


class AudioConverter:
    """
    Audio format converter for Twilio Media Streams.

    Twilio Media Streams use:
    - Format: mulaw (μ-law)
    - Sample rate: 8000 Hz
    - Channels: 1 (mono)
    - Bit depth: 8-bit
    - Encoding: base64
    """

    TWILIO_SAMPLE_RATE = 8000
    TWILIO_CHANNELS = 1

    def to_twilio_format(self, audio_data: bytes, source_rate: int = 8000) -> str:
        """
        Convert audio data to Twilio-compatible format (mulaw base64).

        Args:
            audio_data: Raw audio bytes (expected mulaw if from Azure TTS with correct config)
            source_rate: Source sample rate

        Returns:
            Base64-encoded audio string for Twilio
        """
        try:
            # If Azure TTS is configured correctly, audio is already mulaw 8kHz
            # Just base64 encode it
            return base64.b64encode(audio_data).decode('utf-8')

        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            return ""

    def pcm_to_mulaw(
        self,
        pcm_data: bytes,
        source_rate: int = 16000,
        source_width: int = 2
    ) -> bytes:
        """
        Convert PCM audio to mulaw format.

        Args:
            pcm_data: Raw PCM audio bytes
            source_rate: Source sample rate (Hz)
            source_width: Sample width in bytes (2 = 16-bit)

        Returns:
            Mulaw-encoded audio bytes
        """
        try:
            # Resample to 8kHz if needed
            if source_rate != self.TWILIO_SAMPLE_RATE:
                pcm_data, _ = audioop.ratecv(
                    pcm_data,
                    source_width,
                    self.TWILIO_CHANNELS,
                    source_rate,
                    self.TWILIO_SAMPLE_RATE,
                    None
                )

            # Convert to mulaw
            mulaw_data = audioop.lin2ulaw(pcm_data, source_width)

            return mulaw_data

        except Exception as e:
            logger.error(f"PCM to mulaw conversion error: {e}")
            return b""

    def mulaw_to_pcm(
        self,
        mulaw_data: bytes,
        target_width: int = 2
    ) -> bytes:
        """
        Convert mulaw audio to PCM format.

        Args:
            mulaw_data: Mulaw-encoded audio bytes
            target_width: Target sample width in bytes

        Returns:
            PCM audio bytes
        """
        try:
            pcm_data = audioop.ulaw2lin(mulaw_data, target_width)
            return pcm_data

        except Exception as e:
            logger.error(f"Mulaw to PCM conversion error: {e}")
            return b""

    def from_twilio_format(self, base64_audio: str) -> bytes:
        """
        Decode Twilio audio from base64 mulaw to raw mulaw bytes.

        Args:
            base64_audio: Base64-encoded mulaw audio from Twilio

        Returns:
            Raw mulaw audio bytes
        """
        try:
            return base64.b64decode(base64_audio)
        except Exception as e:
            logger.error(f"Base64 decode error: {e}")
            return b""

    @staticmethod
    def calculate_duration_ms(audio_bytes: bytes, sample_rate: int = 8000) -> int:
        """
        Calculate audio duration in milliseconds.

        Args:
            audio_bytes: Audio data bytes
            sample_rate: Sample rate in Hz

        Returns:
            Duration in milliseconds
        """
        # For mulaw, each byte is one sample
        num_samples = len(audio_bytes)
        duration_seconds = num_samples / sample_rate
        return int(duration_seconds * 1000)
