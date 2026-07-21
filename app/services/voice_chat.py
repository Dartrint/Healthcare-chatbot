"""
Voice Chat Service - Speech-to-text via Groq Whisper, Text-to-speech via edge-tts (free)

- STT: Groq Whisper (whisper-large-v3-turbo) — requires GROQ_API_KEY
- TTS: edge-tts (free, no API key, supports Vietnamese & English)
"""

import asyncio
import base64
import io
import os
import tempfile
from typing import Optional

import groq


# ── helpers ──────────────────────────────────────────────────────────────

def _map_stt_lang(language: str) -> str:
    """Map UI language codes to ISO-639-1 for Groq Whisper."""
    mapping = {
        "vi-VN": "vi",
        "en-US": "en",
        "vi": "vi",
        "en": "en",
    }
    return mapping.get(language, "vi")


def _get_tts_voice(language: str) -> str:
    """Map language to edge-tts voice name."""
    voices = {
        "vi": "vi-VN-HoaiMyNeural",
        "vi-VN": "vi-VN-HoaiMyNeural",
        "en": "en-US-JennyNeural",
        "en-US": "en-US-JennyNeural",
    }
    return voices.get(language, "vi-VN-HoaiMyNeural")


# ── service ──────────────────────────────────────────────────────────────

class VoiceChatService:
    """Service for handling voice input and output.

    Speech-to-text: Groq Whisper API
    Text-to-speech: edge-tts (free, no API key needed)
    """

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.client: Optional[groq.Groq] = None
        if api_key:
            self.client = groq.Groq(api_key=api_key)

        self.stt_model = "whisper-large-v3-turbo"

    # ── availability ──

    def is_available(self) -> bool:
        """Check if Groq API key is configured (required for STT)."""
        return self.client is not None

    # ── speech-to-text (Whisper via Groq) ──

    def transcribe_audio(self, audio_data: bytes, language: str = "vi-VN") -> dict:
        """
        Transcribe audio data to text using Groq Whisper.

        Args:
            audio_data: Raw audio bytes (webm, wav, mp3, ogg, etc.)
            language: Language code (vi-VN or en-US)

        Returns:
            dict with 'text' and 'success' fields
        """
        if not self.client:
            return {
                "success": False,
                "error": "GROQ_API_KEY not configured",
                "text": "",
            }

        try:
            lang = _map_stt_lang(language)

            # Wrap bytes as a file-like object with a name (required by Groq)
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "recording.webm"

            transcription = self.client.audio.transcriptions.create(
                model=self.stt_model,
                file=audio_file,
                language=lang,
            )

            return {
                "success": True,
                "text": transcription.text,
                "language": language,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
            }

    # ── text-to-speech (edge-tts — free, no API key) ──

    def text_to_speech(self, text: str, language: str = "vi") -> dict:
        """
        Convert text to speech audio using edge-tts (free).

        Args:
            text: Text to convert
            language: Language code (vi, vi-VN, en, en-US)

        Returns:
            dict with 'audio_base64', 'success' fields
        """
        try:
            import edge_tts

            voice = _get_tts_voice(language)

            # Run async TTS in a sync context
            async def _run():
                communicate = edge_tts.Communicate(text, voice)
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp_path = tmp.name
                await communicate.save(tmp_path)
                with open(tmp_path, "rb") as f:
                    data = f.read()
                os.unlink(tmp_path)
                return data

            audio_bytes = asyncio.run(_run())
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            return {
                "success": True,
                "audio_base64": audio_base64,
                "language": language,
            }

        except ImportError:
            return {
                "success": False,
                "error": "edge-tts not installed. Run: pip install edge-tts",
                "audio_base64": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "audio_base64": "",
            }