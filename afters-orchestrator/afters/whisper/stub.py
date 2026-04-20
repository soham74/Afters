"""Whisper stub. Deterministic id-to-transcript map so the demo is offline-safe.

The swap point is `transcribe_voice_note`. To wire real Whisper, replace the body
to call `openai.audio.transcriptions.create(...)` with a file pointer. Nothing else
in the Debrief Intake path has to change."""

from __future__ import annotations

_TRANSCRIPTS: dict[str, str] = {}


def register_voice_note(ref: str, transcript: str) -> None:
    _TRANSCRIPTS[ref] = transcript


def transcribe_voice_note(ref: str) -> str:
    if ref not in _TRANSCRIPTS:
        return (
            "honestly it was really nice. we got like three hours of just talking. "
            "i'd see them again for sure."
        )
    return _TRANSCRIPTS[ref]
