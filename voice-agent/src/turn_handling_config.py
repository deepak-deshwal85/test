"""LiveKit AgentSession turn handling configuration.

See https://docs.livekit.io/reference/agents/turn-handling-options/
"""

import os

from livekit.agents import TurnHandlingOptions, inference
from livekit.agents.voice.turn import (
    EndpointingOptions,
    InterruptionOptions,
    PreemptiveGenerationOptions,
)

from client_config import ClientConfig
from rag_client.prefetch import requires_sync_turn_completion

# TurnDetector audio endpointing uses 0.3s / 2.5s SDK defaults; we keep a
# shorter max_delay for outbound phone calls unless overridden via env.
DEFAULT_TURN_ENDPOINTING_MIN_DELAY = 0.3
DEFAULT_TURN_ENDPOINTING_MAX_DELAY = 1.0
DEFAULT_TURN_ENDPOINTING_MODE = "dynamic"
DEFAULT_TURN_ENDPOINTING_ALPHA = 0.9

DEFAULT_INTERRUPTION_MODE = "adaptive"
DEFAULT_FALSE_INTERRUPTION_TIMEOUT = 2.0

DEFAULT_PREEMPTIVE_MAX_SPEECH_DURATION = 10.0
DEFAULT_PREEMPTIVE_MAX_RETRIES = 3


def _float_env(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _int_env(name: str, default: int) -> int:
    return int(_float_env(name, float(default)))


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def build_endpointing_options() -> EndpointingOptions:
    mode = os.getenv("TURN_ENDPOINTING_MODE", DEFAULT_TURN_ENDPOINTING_MODE)
    if mode not in {"fixed", "dynamic"}:
        mode = DEFAULT_TURN_ENDPOINTING_MODE
    return EndpointingOptions(
        mode=mode,
        min_delay=_float_env(
            "TURN_ENDPOINTING_MIN_DELAY", DEFAULT_TURN_ENDPOINTING_MIN_DELAY
        ),
        max_delay=_float_env(
            "TURN_ENDPOINTING_MAX_DELAY", DEFAULT_TURN_ENDPOINTING_MAX_DELAY
        ),
        alpha=_float_env("TURN_ENDPOINTING_ALPHA", DEFAULT_TURN_ENDPOINTING_ALPHA),
    )


def build_interruption_options() -> InterruptionOptions:
    mode = os.getenv("TURN_INTERRUPTION_MODE", DEFAULT_INTERRUPTION_MODE)
    if mode not in {"adaptive", "vad"}:
        mode = DEFAULT_INTERRUPTION_MODE
    return InterruptionOptions(
        mode=mode,
        resume_false_interruption=_bool_env("TURN_RESUME_FALSE_INTERRUPTION", True),
        false_interruption_timeout=_float_env(
            "TURN_FALSE_INTERRUPTION_TIMEOUT", DEFAULT_FALSE_INTERRUPTION_TIMEOUT
        ),
    )


def build_preemptive_generation_options(
    *, requires_sync: bool
) -> PreemptiveGenerationOptions:
    if requires_sync:
        # RAG prefetch in on_user_turn_completed must finish before the LLM runs.
        return PreemptiveGenerationOptions(enabled=False)
    return PreemptiveGenerationOptions(
        enabled=True,
        preemptive_tts=_bool_env("TURN_PREEMPTIVE_TTS", False),
        max_speech_duration=_float_env(
            "TURN_PREEMPTIVE_MAX_SPEECH_DURATION",
            DEFAULT_PREEMPTIVE_MAX_SPEECH_DURATION,
        ),
        max_retries=_int_env(
            "TURN_PREEMPTIVE_MAX_RETRIES", DEFAULT_PREEMPTIVE_MAX_RETRIES
        ),
    )


def build_turn_handling_options(client_config: ClientConfig) -> TurnHandlingOptions:
    requires_sync = requires_sync_turn_completion(client_config)
    return TurnHandlingOptions(
        turn_detection=inference.TurnDetector(version="v1"),
        endpointing=build_endpointing_options(),
        interruption=build_interruption_options(),
        preemptive_generation=build_preemptive_generation_options(
            requires_sync=requires_sync
        ),
    )
