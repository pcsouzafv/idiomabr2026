"""OpenAI Text-to-Speech (TTS) service.

This replaces ElevenLabs usage for /api/conversation/tts.
DeepSeek remains available for chat (LLM) via OpenAI-compatible base_url.

Voices supported by OpenAI TTS (as of current SDK): alloy, echo, fable, onyx, nova, shimmer
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal, cast

import httpx

from app.core.config import get_settings

try:
    from openai import OpenAI  # type: ignore
    from openai import APIStatusError  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore
    APIStatusError = None  # type: ignore


class OpenAITTSService:
    DEFAULT_MODEL = "tts-1"
    DEFAULT_VOICE = "nova"
    SUPPORTED_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.lemonfox_api_key = getattr(settings, "lemonfox_api_key", "")
        self.lemonfox_base_url = (getattr(settings, "lemonfox_base_url", "") or "https://api.lemonfox.ai/v1").strip()
        self.lemonfox_enabled = bool(getattr(settings, "lemonfox_enabled", False))
        # Important: force a TTS base_url so we don't inherit any OpenAI-compatible LLM base_url
        # (e.g. DeepSeek) from environment variables.
        self.base_url = (getattr(settings, "openai_tts_base_url", "") or "https://api.openai.com/v1").strip()
        self.default_model = (getattr(settings, "openai_tts_model", "") or self.DEFAULT_MODEL).strip()

        self.client = (
            OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=30.0,
                max_retries=2,
            )
            if (OpenAI is not None and self.api_key)
            else None
        )

    def _check_ready(self) -> None:
        if self.lemonfox_enabled and self.lemonfox_api_key:
            return
        if OpenAI is None:
            raise ValueError("Biblioteca OpenAI não está instalada no backend")
        if not self.api_key:
            raise ValueError("TTS requer LEMONFOX_API_KEY ou OPENAI_API_KEY configurada no .env")
        if self.client is None:
            raise ValueError("Cliente OpenAI não inicializado")

    def list_voices(self) -> List[Dict[str, Any]]:
        if self.lemonfox_enabled and self.lemonfox_api_key:
            lemonfox_voices = [
                "heart",
                "bella",
                "michael",
                "alloy",
                "aoede",
                "kore",
                "jessica",
                "nicole",
                "nova",
                "river",
                "sarah",
                "sky",
                "echo",
                "eric",
                "fenrir",
                "liam",
                "onyx",
                "puck",
                "adam",
                "santa",
            ]
            return [{"voice_id": v, "name": v} for v in lemonfox_voices]
        # OpenAI TTS voices are currently fixed strings.
        return [{"voice_id": v, "name": v} for v in self.SUPPORTED_VOICES]

    def text_to_speech(
        self,
        *,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        # voice_settings not used by OpenAI TTS today; kept for compatibility with existing schema.
        _ = voice_settings

        self._check_ready()

        if not text or not text.strip():
            raise ValueError("Texto vazio para TTS")

        voice = (voice_id or self.DEFAULT_VOICE).strip().lower()
        if not (self.lemonfox_enabled and self.lemonfox_api_key) and voice not in self.SUPPORTED_VOICES:
            raise ValueError(
                f"Voz inválida '{voice}'. Use uma de: {', '.join(self.SUPPORTED_VOICES)}"
            )

        # Lemonfox path (OpenAI-compatible HTTP but no SDK required here)
        if self.lemonfox_enabled and self.lemonfox_api_key:
            safe_text = text.strip()[:4096]
            response = httpx.post(
                f"{self.lemonfox_base_url}/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.lemonfox_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": safe_text,
                    "voice": voice,
                    "response_format": "mp3",
                    "language": "en-us",
                    "speed": 0.95,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.content

        # Help type-checkers: voice is guaranteed to be one of the supported literals.
        voice_literal = cast(
            Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            voice,
        )

        model = (model_id or self.default_model or self.DEFAULT_MODEL).strip()
        # If the configured/default model isn't available in the account, try a small fallback list.
        models_to_try = [model]
        for fallback in (self.DEFAULT_MODEL, "gpt-4o-mini-tts"):
            if fallback and fallback not in models_to_try:
                models_to_try.append(fallback)

        # OpenAI TTS has an input length limit; keep it safe.
        safe_text = text.strip()[:4096]

        # Help type-checkers: _check_ready() guarantees client is initialized.
        client = cast(Any, self.client)

        last_exc: Exception | None = None
        for model_name in models_to_try:
            try:
                response = client.audio.speech.create(
                    model=model_name,
                    voice=voice_literal,
                    input=safe_text,
                    # Slightly slower helps learners.
                    speed=0.95,
                )

                return response.content
            except Exception as e:  # Let the route map status codes nicely.
                # If model is not found/available, try the next fallback model.
                if APIStatusError is not None and isinstance(e, APIStatusError):
                    status_code = getattr(e, "status_code", None)
                    msg = str(e).lower()
                    if status_code == 404 and ("model" in msg or "not found" in msg):
                        last_exc = e
                        continue
                raise

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Falha inesperada ao gerar áudio")


openai_tts_service = OpenAITTSService()
