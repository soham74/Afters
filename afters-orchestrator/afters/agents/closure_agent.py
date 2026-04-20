"""Closure Agent.

sonnet-4-5. Drafts a short, dignified message to the interested party in an
asymmetric outcome. Never shares information the less-interested party did not
consent to share. Routes through a human-in-the-loop review queue (not auto-sent).

Hard rules baked into the prompt:
- Gen Z casual, lowercase, short sentences.
- No em dashes.
- No exclamation points unless genuinely warm.
- Don't repeat the less-interested party's exact words verbatim.
- Never say "they weren't into you" or anything that could wound; stay dignified.
"""

from __future__ import annotations

from afters.llm.client import get_llm
from afters.models import AftersOutcome, ClosureDraft, DebriefExtraction

SYSTEM = """You are the Closure Agent for Afters (Ditto's post-date system).

You draft closure messages for the user who signaled more interest in continued contact when the other person signaled less. There are three asymmetric cases:

- Again vs Pass: the recipient wanted another one-on-one date. the other person opted out entirely.
- Again vs Group: the recipient wanted another one-on-one. the other person wanted a lower-stakes group hang instead.
- Group vs Pass: the recipient wanted a group hang (not one-on-one). the other person opted out entirely. the recipient is still the interested party. do NOT describe the recipient as having felt a "friend vibe" - that is the other person's signal, not theirs. the recipient actively wanted to keep meeting in a group setting.

Your tone is Gen Z casual, short, warm, dignified. You protect the other user's privacy: you do NOT share their specific words or reasons verbatim, only sanitized abstractions ("they felt more like a friend vibe", not "they said you talked about your ex too much").

Hard rules:
- lowercase only but keep apostrophes in contractions (don't, you'll, i'd, we'll, aren't).
- no em dashes.
- no exclamation points unless the sentence is genuinely warm and celebratory (rare for closure messages).
- sentences short. the whole message fits in a text bubble. aim 40 to 90 words.
- no "i'm sorry but" phrasing. it should feel honest, not clinical and not sappy.
- end with a forward-looking line about future matches if appropriate, but don't make promises.
"""


CHOICE_INTERPRETATION: dict[str, str] = {
    "again": "another one-on-one date with the other person",
    "group": "continued contact with the other person, in a group setting",
    "pass": "no further contact",
}


REROUTE_HINT_BY_OUTCOME: dict[str, str] = {
    "asymmetric_again_pass": (
        "keep it purely a closure message. do not offer a group hang; the recipient "
        "did not ask for one and the other person declined outright."
    ),
    "asymmetric_again_group": (
        "the other person still picked group, so after the closure line, offer the "
        "recipient a group hang reroute as a soft option. they wanted one-on-one, "
        "so frame it as 'if you're open to it' rather than a default."
    ),
    "asymmetric_group_pass": (
        "the recipient already picked group, so offer to put them in the group "
        "queue for next week's group hang so they can still meet other group-vibe "
        "people. frame it as the natural next step, not a consolation prize. "
        "acknowledge that the other person isn't part of this reroute."
    ),
}


def _sanitize_reason(concerns: list[str]) -> str:
    """Pick a single non-identifying concern, or a generic phrase if none fit."""
    if not concerns:
        return "more of a friend vibe for them"
    safe = [c for c in concerns if len(c) < 60 and "ex" not in c.lower()]
    return safe[0] if safe else "more of a friend vibe for them"


def _build_summary(recipient_name: str):
    def summarize(parsed: ClosureDraft, latency_ms: int) -> str:
        words = len(parsed.message.split())
        return (
            f"Closure Agent drafted a {words}-word message for {recipient_name} "
            f"in {latency_ms}ms using sonnet, queued for human review."
        )

    return summarize


async def run_closure_agent(
    *,
    session_id: str,
    recipient_name: str,
    recipient_choice: str,
    other_choice: str,
    outcome: AftersOutcome,
    recipient_debrief: DebriefExtraction | None,
    other_debrief: DebriefExtraction | None,
    regeneration_seed: int = 0,
    scenario_mock_tag: str | None = None,
) -> ClosureDraft:
    sanitized = _sanitize_reason(other_debrief.concerns if other_debrief else [])
    reroute_hint = REROUTE_HINT_BY_OUTCOME.get(
        outcome,
        "keep it purely a closure message. do not offer a group hang.",
    )
    recipient_meaning = CHOICE_INTERPRETATION.get(recipient_choice, recipient_choice)
    other_meaning = CHOICE_INTERPRETATION.get(other_choice, other_choice)

    user_msg = (
        f"Outcome: {outcome}.\n"
        f"Recipient: {recipient_name}. they picked '{recipient_choice}', meaning "
        f"they wanted {recipient_meaning}.\n"
        f"The other person picked '{other_choice}', meaning they wanted "
        f"{other_meaning}.\n"
        f"Sanitized reason (safe to paraphrase, not quote): {sanitized}\n"
        f"Recipient's stated interest level: "
        f"{recipient_debrief.interest_level if recipient_debrief else '?'}/10\n"
        f"Regeneration seed: {regeneration_seed} "
        "(if greater than 0, try a visibly different angle from the last draft).\n\n"
        f"{reroute_hint}\n\n"
        "Write the closure message. Frame the recipient's choice as the interested "
        "signal; do not invert who wanted what."
    )

    return await get_llm().structured(
        agent_name="Closure Agent",
        session_id=session_id,
        model="claude-sonnet-4-5",
        system=SYSTEM,
        user=user_msg,
        schema_cls=ClosureDraft,
        tool_name="emit_closure_draft",
        tool_description="Emit the draft closure message for human review.",
        summary_builder=_build_summary(recipient_name),
        input_summary=f"{recipient_name}; {outcome}; regen={regeneration_seed}",
        mock_tag=scenario_mock_tag,
        temperature=0.7 if regeneration_seed > 0 else 0.4,
        tags=["closure_agent", "sonnet", outcome, f"regen:{regeneration_seed}"],
    )


def fallback_closure_message(recipient_name: str) -> str:
    """Used after the second reject. Deterministic, gentle, generic."""
    return (
        f"hey {recipient_name.split()[0].lower()}, just a quick check in from afters. "
        "looks like this one wasn't a match for a second date. hope it still felt like a "
        "fun night. we'll keep an eye out for someone who fits better next wednesday."
    )
