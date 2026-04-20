"""Debrief Intake Agent.

Claude haiku-4-5 with a Pydantic-typed tool. Takes a raw text reply (or a Whisper
transcript) from one user after a first date. Emits a structured debrief:
interest_level, choice, wants_second_date, willing_to_group_hang, memorable_moments,
concerns, free_text_note.

Called once per user per session. Two parallel runs are the norm.
"""

from __future__ import annotations

from afters.llm.client import get_llm
from afters.models import DebriefExtraction

SYSTEM = """You are the Debrief Intake agent for Afters, Ditto's post-date feedback system.

Your job: extract a structured debrief from a college student's short message (text or voice-note transcript) about a first date they just went on.

Rules:
- Pick exactly one choice from {again, group, pass}. "again" means they want a second one-on-one date. "group" means they liked the person but want lower stakes and a group hang. "pass" means no second date.
- interest_level is 0 (no spark, would not repeat) to 10 (giddy, cant stop talking about it). Be calibrated, not generous.
- memorable_moments: 1 to 4 short phrases that cite specific things the user mentioned (not your paraphrase). Lowercase, no punctuation at the end.
- concerns: 0 to 3 short phrases summarizing anything that gave them pause. Leave empty if none.
- wants_second_date and willing_to_group_hang are booleans derived from the same signal as choice but recorded separately because the downstream router reads them independently.
- free_text_note: one-sentence paraphrase of what the user said, first-person-reported style. Under 280 chars. Lowercase. No em dashes.
"""


def _build_summary(user_name: str, is_voice_note: bool):
    def summarize(parsed: DebriefExtraction, latency_ms: int) -> str:
        kind = "voice note" if is_voice_note else "text reply"
        return (
            f"Debrief Intake extracted interest_level {parsed.interest_level} "
            f"and choice={parsed.choice} from {user_name}'s {kind} "
            f"in {latency_ms}ms using haiku."
        )

    return summarize


async def run_debrief_intake(
    *,
    session_id: str,
    user_id: str,
    user_name: str,
    reply_text: str,
    is_voice_note: bool = False,
    scenario_mock_tag: str | None = None,
) -> DebriefExtraction:
    user_msg = (
        f"User: {user_name}\n"
        f"Reply ({'voice note transcript' if is_voice_note else 'text'}):\n"
        f'"{reply_text}"\n\n'
        "Extract the debrief."
    )
    return await get_llm().structured(
        agent_name="Debrief Intake",
        session_id=session_id,
        model="claude-haiku-4-5",
        system=SYSTEM,
        user=user_msg,
        schema_cls=DebriefExtraction,
        tool_name="emit_debrief",
        tool_description="Emit the structured post-date debrief for this user.",
        summary_builder=_build_summary(user_name, is_voice_note),
        input_summary=(
            f"{user_name}: "
            f"{reply_text[:80]}{'...' if len(reply_text) > 80 else ''}"
        ),
        mock_tag=scenario_mock_tag,
        tags=["debrief_intake", "haiku", f"user:{user_id}"],
    )
