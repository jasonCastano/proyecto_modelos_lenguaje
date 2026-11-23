"""Dictado por voz para Valer-IA Caña (spec 023, ADR 0027).

La voz del visitante llega como WAV PCM16 mono a 16 kHz, se transcribe en el servidor con
faster-whisper (sin terceros) y vuelve como texto al campo del chat. El audio vive solo en memoria.
"""

from .config import SttConfig, SttConfigError, load_stt_config

__all__ = ["SttConfig", "SttConfigError", "load_stt_config"]
