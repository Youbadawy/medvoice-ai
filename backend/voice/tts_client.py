"""
MedVoice AI - Google Cloud TTS Client
Text-to-speech synthesis with French-Canadian and English voices.
Uses existing Firebase/GCP credentials.
"""

import asyncio
import logging
from typing import Optional
from google.cloud import texttospeech

logger = logging.getLogger(__name__)


class GoogleTTSClient:
    """
    Google Cloud TTS client for bilingual voice synthesis.
    Supports French-Canadian and English-Canadian Wavenet voices.
    """

    # Voice mappings - Wavenet voices for natural speech
    VOICES = {
        "fr-CA": {
            "female": "fr-CA-Wavenet-A",
            "male": "fr-CA-Wavenet-B"
        },
        "en-CA": {
            "female": "en-CA-Wavenet-A",
            "male": "en-CA-Wavenet-B"
        }
    }

    def __init__(self, voice_gender: str = "female"):
        """
        Initialize Google Cloud TTS client.
        Uses GOOGLE_APPLICATION_CREDENTIALS environment variable for auth.

        Args:
            voice_gender: 'female' or 'male'
        """
        self.voice_gender = voice_gender
        self.client = texttospeech.TextToSpeechClient()

    async def synthesize(self, text: str, language: str = "fr-CA") -> Optional[bytes]:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize
            language: Language code ('fr-CA' or 'en-CA')

        Returns:
            Audio bytes in mulaw format, or None on error
        """
        if not text:
            return None

        try:
            # Get appropriate voice
            voice_name = self._get_voice(language)

            # Set up the synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=language,
                name=voice_name
            )

            # Select the audio encoding - mulaw 8kHz for Twilio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MULAW,
                sample_rate_hertz=8000
            )

            # Run synthesis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
            )

            logger.debug(f"TTS synthesis completed for: {text[:50]}...")
            return response.audio_content

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return None

    async def synthesize_ssml(self, ssml: str, language: str = "fr-CA") -> Optional[bytes]:
        """
        Synthesize SSML to speech.
        Use for advanced control over prosody, pauses, etc.

        Args:
            ssml: SSML markup string
            language: Language code for voice selection

        Returns:
            Audio bytes in mulaw format, or None on error
        """
        try:
            voice_name = self._get_voice(language)

            # Set up the synthesis input with SSML
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=language,
                name=voice_name
            )

            # Select the audio encoding - mulaw 8kHz for Twilio
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MULAW,
                sample_rate_hertz=8000
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice,
                    audio_config=audio_config
                )
            )

            return response.audio_content

        except Exception as e:
            logger.error(f"SSML synthesis error: {e}")
            return None

    def _get_voice(self, language: str) -> str:
        """Get the appropriate voice name for the language and gender."""
        lang_voices = self.VOICES.get(language, self.VOICES["fr-CA"])
        return lang_voices.get(self.voice_gender, lang_voices["female"])

    def build_ssml(
        self,
        text: str,
        language: str = "fr-CA",
        rate: str = "medium",
        pitch: str = "medium"
    ) -> str:
        """
        Build SSML markup for more natural speech.

        Args:
            text: Text to speak
            language: Language code
            rate: Speech rate (x-slow, slow, medium, fast, x-fast)
            pitch: Voice pitch (x-low, low, medium, high, x-high)

        Returns:
            SSML string
        """
        # Map rate names to percentages for Google Cloud TTS
        rate_map = {
            "x-slow": "50%",
            "slow": "75%",
            "medium": "100%",
            "fast": "125%",
            "x-fast": "150%"
        }

        # Map pitch names to semitones
        pitch_map = {
            "x-low": "-4st",
            "low": "-2st",
            "medium": "0st",
            "high": "+2st",
            "x-high": "+4st"
        }

        rate_value = rate_map.get(rate, "100%")
        pitch_value = pitch_map.get(pitch, "0st")

        ssml = f"""
<speak>
    <prosody rate="{rate_value}" pitch="{pitch_value}">
        {text}
    </prosody>
</speak>
"""
        return ssml.strip()


# Alias for backwards compatibility
TTSClient = GoogleTTSClient
