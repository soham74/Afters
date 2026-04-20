"""Run the Debrief Intake Agent against the hand-labeled eval set.

Reports:
- Overall accuracy on the `choice` field.
- Precision + recall for `wants_second_date` (treating True as positive class).
- Precision + recall for `willing_to_group_hang` (treating True as positive class).
- A small confusion matrix on choice.
- Cumulative cost + latency.

Usage:
    cd afters-orchestrator && python -m evals.run_evals
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import Counter

from afters.agents.debrief_intake import run_debrief_intake
from afters.config import get_settings
from afters.db.mongo import get_db
from evals.dataset import DATASET, Example


def _prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


async def run():
    # Use the sessionless trace path; agent_traces still get written so you can
    # inspect eval LLM traffic in the dashboard's Traces view.
    settings = get_settings()
    print(f"Running {len(DATASET)} eval examples (MOCK_LLM={settings.mock_llm})")

    # Ensure a synthetic session id so traces group together in the dashboard.
    eval_session_id = "eval_" + str(int(time.time()))

    # Insert a placeholder session so the traces page doesn't point nowhere.
    # (The orchestrator treats unknown session_ids gracefully; we skip inserting
    #  since the Traces view doesn't require a joined session.)

    rows = []
    cost_total = 0.0
    latency_total = 0
    choice_confusion: Counter = Counter()  # (expected, predicted) -> count
    wants_tp = wants_fp = wants_fn = 0
    group_tp = group_fp = group_fn = 0
    choice_correct = 0

    for ex in DATASET:
        t0 = time.perf_counter()
        try:
            extraction = await run_debrief_intake(
                session_id=eval_session_id,
                user_id=ex.id,
                user_name=ex.id,
                reply_text=ex.reply,
                is_voice_note=ex.is_voice_note,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  {ex.id}: ERROR {exc}")
            continue
        latency_ms = int((time.perf_counter() - t0) * 1000)
        latency_total += latency_ms

        pred_choice = extraction.choice
        pred_wants = extraction.wants_second_date
        pred_group = extraction.willing_to_group_hang

        choice_confusion[(ex.expected_choice, pred_choice)] += 1
        if pred_choice == ex.expected_choice:
            choice_correct += 1

        if ex.expected_wants_second and pred_wants:
            wants_tp += 1
        elif not ex.expected_wants_second and pred_wants:
            wants_fp += 1
        elif ex.expected_wants_second and not pred_wants:
            wants_fn += 1

        if ex.expected_willing_group and pred_group:
            group_tp += 1
        elif not ex.expected_willing_group and pred_group:
            group_fp += 1
        elif ex.expected_willing_group and not pred_group:
            group_fn += 1

        rows.append(
            {
                "id": ex.id,
                "expected": {
                    "choice": ex.expected_choice,
                    "wants_second_date": ex.expected_wants_second,
                    "willing_to_group_hang": ex.expected_willing_group,
                },
                "predicted": {
                    "choice": pred_choice,
                    "wants_second_date": pred_wants,
                    "willing_to_group_hang": pred_group,
                    "interest_level": extraction.interest_level,
                },
                "latency_ms": latency_ms,
                "correct_choice": pred_choice == ex.expected_choice,
            }
        )

    total = len(rows)
    print()
    print("=== Results ===")
    print(f"choice accuracy : {choice_correct}/{total} = {choice_correct / total:.3f}")
    print()
    print("wants_second_date:")
    print("  " + json.dumps(_prf(wants_tp, wants_fp, wants_fn), indent=2).replace("\n", "\n  "))
    print()
    print("willing_to_group_hang:")
    print("  " + json.dumps(_prf(group_tp, group_fp, group_fn), indent=2).replace("\n", "\n  "))
    print()
    print("choice confusion matrix (rows=expected, cols=predicted):")
    labels = ["again", "group", "pass"]
    print("                " + "  ".join(f"{c:>6}" for c in labels))
    for expected in labels:
        row = [choice_confusion.get((expected, p), 0) for p in labels]
        print(f"  {expected:>12}  " + "  ".join(f"{v:>6}" for v in row))
    print()
    print(f"total latency   : {latency_total}ms")
    print(f"avg latency     : {latency_total / total:.0f}ms per example")
    return rows


if __name__ == "__main__":
    asyncio.run(run())
