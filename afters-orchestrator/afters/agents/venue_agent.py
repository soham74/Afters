"""Venue Agent.

sonnet-4-5 with RAG over the seeded venue collection. Input is both users'
intersected memorable_moments and concerns plus the first-date venue. Output is
exactly 3 ranked venue picks with one-sentence reasons per pick.

Retrieval is tag-intersection (not embeddings), on purpose: it stays deterministic
for the demo and the ranking story is "agent picks from a retrieved candidate set,"
not "agent does semantic search." Swap-in point is `retrieve_candidates`.
"""

from __future__ import annotations

from afters.db.mongo import collections, get_db
from afters.llm.client import get_llm
from afters.models import Campus, DebriefExtraction, Venue, VenueRanking

SYSTEM = """You are the Venue Agent for Afters (Ditto's post-date follow-up system).

Your job: given what two college students said made their first date work, pick 3 second-date venues from a retrieved candidate list. Rank them best-fit first.

Rules:
- Reply with exactly 3 picks.
- Each pick: one venue_id from the candidate list, and one sentence explaining why it fits THIS specific pair. Cite their actual phrasing where possible.
- Prefer venues that resolve concerns. If one user flagged "too loud" and another said they wanted to "keep talking", pick something quieter, not another bar.
- Do not suggest the same venue as the first date.
- Keep reason sentences lowercase and under 180 chars. No em dashes.
"""


def _shared_themes(a: DebriefExtraction, b: DebriefExtraction) -> list[str]:
    """Intersect memorable moments across the two debriefs (case-insensitive)."""
    a_set = {m.lower() for m in a.memorable_moments}
    b_set = {m.lower() for m in b.memorable_moments}
    return sorted(a_set & b_set) or sorted(a_set | b_set)[:3]


def _union_concerns(a: DebriefExtraction, b: DebriefExtraction) -> list[str]:
    return sorted({c.lower() for c in (a.concerns + b.concerns)})


async def retrieve_candidates(
    campus: Campus,
    shared_moments: list[str],
    exclude_venue_id: str,
    limit: int = 8,
) -> list[Venue]:
    """Tag-intersection retrieval. Pulls venues whose tags overlap with any token
    in shared_moments; falls back to top-rated-by-tag-count on the campus."""
    db = get_db()
    tokens = {
        t
        for m in shared_moments
        for t in m.lower().replace(",", " ").split()
        if len(t) > 2
    }
    cursor = db[collections.venues].find(
        {
            "campus": campus,
            "_id": {"$ne": exclude_venue_id},
        }
    )
    rows = [Venue.model_validate(r) async for r in cursor]

    def score(v: Venue) -> int:
        return sum(1 for tag in v.tags if any(tok in tag.lower() for tok in tokens))

    rows.sort(key=score, reverse=True)
    return rows[:limit]


def _format_candidate(v: Venue) -> str:
    return (
        f"- id={v.id} | {v.name} ({v.type}) "
        f"| tags: {', '.join(v.tags)} | vibe: {v.vibe} "
        f"| {v.walking_distance_from_campus_min} min from campus"
    )


def _build_summary(top_name_lookup: dict[str, str]):
    def summarize(parsed: VenueRanking, latency_ms: int) -> str:
        top = parsed.picks[0]
        top_name = top_name_lookup.get(top.venue_id, top.venue_id)
        return (
            f"Venue Agent ranked 3 second-date picks "
            f"(top: {top_name}, because {_trim_reason(top.reason)}) "
            f"in {latency_ms}ms using sonnet."
        )

    return summarize


def _trim_reason(reason: str, limit: int = 80) -> str:
    return reason if len(reason) <= limit else reason[: limit - 1] + "…"


async def run_venue_agent(
    *,
    session_id: str,
    campus: Campus,
    user_a_name: str,
    user_b_name: str,
    user_a_debrief: DebriefExtraction,
    user_b_debrief: DebriefExtraction,
    first_date_venue: Venue,
    scenario_mock_tag: str | None = None,
) -> VenueRanking:
    shared = _shared_themes(user_a_debrief, user_b_debrief)
    concerns = _union_concerns(user_a_debrief, user_b_debrief)
    candidates = await retrieve_candidates(
        campus=campus,
        shared_moments=shared,
        exclude_venue_id=first_date_venue.id,
    )

    candidate_block = "\n".join(_format_candidate(v) for v in candidates)

    user_msg = (
        f"Campus: {campus}\n"
        f"Pair: {user_a_name} + {user_b_name}\n"
        f"Shared moments (both said some version of this): {shared}\n"
        f"Combined concerns: {concerns or 'none'}\n"
        f"First-date venue: {first_date_venue.name} ({first_date_venue.vibe})\n\n"
        f"Candidate venues retrieved by tag overlap:\n{candidate_block}\n\n"
        "Pick 3 ranked venues."
    )

    name_lookup = {v.id: v.name for v in candidates}

    return await get_llm().structured(
        agent_name="Venue Agent",
        session_id=session_id,
        model="claude-sonnet-4-5",
        system=SYSTEM,
        user=user_msg,
        schema_cls=VenueRanking,
        tool_name="emit_venue_ranking",
        tool_description="Emit 3 ranked second-date venue picks.",
        summary_builder=_build_summary(name_lookup),
        input_summary=f"{user_a_name}+{user_b_name} @ {campus}; {len(candidates)} candidates",
        mock_tag=scenario_mock_tag,
        tags=["venue_agent", "sonnet", "rag"],
    )
