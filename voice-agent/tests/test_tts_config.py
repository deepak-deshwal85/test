import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tts_config import (
    DEFAULT_CARTESIA_TTS_MODEL,
    DEFAULT_CARTESIA_TTS_VOICE,
    build_cartesia_tts,
)


def test_build_cartesia_tts_uses_defaults():
    with patch.dict(
        os.environ,
        {"CARTESIA_API_KEY": "test-cartesia-key"},
        clear=True,
    ):
        tts = build_cartesia_tts()
    assert tts._opts.model == DEFAULT_CARTESIA_TTS_MODEL
    assert tts._opts.voice == DEFAULT_CARTESIA_TTS_VOICE
    assert tts._opts.language == "en"


def test_build_cartesia_tts_reads_env_overrides():
    with patch.dict(
        os.environ,
        {
            "CARTESIA_API_KEY": "test-cartesia-key",
            "CARTESIA_TTS_MODEL": "sonic-2",
            "CARTESIA_TTS_VOICE": "voice-123",
        },
        clear=True,
    ):
        tts = build_cartesia_tts()
    assert tts._opts.model == "sonic-2"
    assert tts._opts.voice == "voice-123"
