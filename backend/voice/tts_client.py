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
    Uses Journey voices for most natural, human-like speech.
    """

    # Voice mappings - Journey voices for most natural speech
    # Journey voices are Google's premium conversational voices
    VOICES = {
        "fr-CA": {
            "female": "fr-CA-Journey-F",   # Journey French-Canadian female
            "male": "fr-CA-Journey-D"      # Journey French-Canadian male
        },
        "en-US": {
            "female": "en-US-Journey-F",   # Journey English female (warm, friendly)
            "male": "en-US-Journey-D"      # Journey English male
        }
    }

    # Fallback to Neural2 if Journey not available
    FALLBACK_VOICES = {
        "fr-CA": {
            "female": "fr-CA-Neural2-A",
            "male": "fr-CA-Neural2-B"
        },
        "en-US": {
            "female": "en-US-Neural2-F",
            "male": "en-US-Neural2-D"
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

        # Normalize text (remove markdown, expand abbrevs)
        text = self._normalize_text(text, language)

        # Normalize language codes - map en-CA to en-US (we don't have en-CA voices)
        normalized_language = self._normalize_language(language)

        # Try Journey voices first, fall back to Neural2 if needed
        for use_fallback in [False, True]:
            try:
                voice_name = self._get_voice(normalized_language, use_fallback=use_fallback)
                logger.info(f"🔊 TTS using voice: {voice_name} (language: {normalized_language})")

                # Set up the synthesis input
                synthesis_input = texttospeech.SynthesisInput(text=text)

                # Build the voice request
                voice = texttospeech.VoiceSelectionParams(
                    language_code=normalized_language,
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

                logger.info(f"🔊 TTS synthesis completed for: {text[:50]}...")
                return response.audio_content

            except Exception as e:
                if use_fallback:
                    logger.error(f"❌ TTS synthesis error (fallback failed): {e}")
                    return None
                else:
                    logger.warning(f"⚠️ Journey voice failed, trying fallback: {e}")
                    continue

        return None

    def _normalize_text(self, text: str, language: str) -> str:
        """
        Normalize text for speech:
        - Remove markdown bold/italic (**, *)
        - Remove list markers (- )
        - Expand common abbreviations
        """
        import re
        
        # Remove bold/italic markers
        text = text.replace("**", "").replace("*", "")
        
        # Remove list dashes at start of lines
        text = re.sub(r'^\s*-\s+', '', text, flags=re.MULTILINE)
        
        # Expand abbreviations based on language
        if "fr" in language:
            text = text.replace("e.g.", "par exemple")
            text = text.replace("c.-à-d.", "c'est-à-dire")
        else:
            text = text.replace("e.g.", "for example")
            text = text.replace("i.e.", "that is")
            
        return text

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
            # Normalize language codes
            normalized_language = self._normalize_language(language)
            voice_name = self._get_voice(normalized_language)

            # Set up the synthesis input with SSML
            synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=normalized_language,
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

    def _normalize_language(self, language: str) -> str:
        """
        Normalize language codes to supported TTS languages.
        Maps en-CA to en-US since we don't have Canadian English voices.
        """
        # Map unsupported language codes to supported ones
        language_map = {
            "en-CA": "en-US",  # Canadian English -> US English
            "en": "en-US",     # Generic English -> US English
            "fr": "fr-CA",     # Generic French -> Canadian French
        }
        return language_map.get(language, language)

    def _get_voice(self, language: str, use_fallback: bool = False) -> str:
        """Get the appropriate voice name for the language and gender."""
        voices = self.FALLBACK_VOICES if use_fallback else self.VOICES
        lang_voices = voices.get(language, voices["fr-CA"])
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
