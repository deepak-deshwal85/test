import os

from livekit.plugins import cartesia

DEFAULT_CARTESIA_TTS_MODEL = "sonic-3.5"
# Cartesia plugin default English voice (see livekit.plugins.cartesia.TTS).
DEFAULT_CARTESIA_TTS_VOICE = "f786b574-daa5-4673-aa0c-cbe3e8534c02"


def build_cartesia_tts(
    *,
    model: str | None = None,
    voice: str | None = None,
    language: str = "en",
) -> cartesia.TTS:
    return cartesia.TTS(
        model=model or os.getenv("CARTESIA_TTS_MODEL", DEFAULT_CARTESIA_TTS_MODEL),
        voice=voice or os.getenv("CARTESIA_TTS_VOICE", DEFAULT_CARTESIA_TTS_VOICE),
        language=language,
    )
