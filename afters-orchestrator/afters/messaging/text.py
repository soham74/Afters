"""Text helpers shared by every user-facing iMessage template.

Keeps the Ditto voice consistent: lowercase-casual with correct apostrophes,
no em dashes, no exclamation points, and datetimes rendered the way humans read
them ("Mon Apr 20 at 6pm", not "2026-04-20 at 18:00").
"""

from __future__ import annotations

from datetime import datetime


def fmt_dt(value: str | datetime) -> str:
    """Render a datetime as 'Mon Apr 20 at 6pm' (or 'Mon Apr 20 at 6:30pm').

    Accepts either an ISO-8601 string or a datetime. Twelve-hour clock, lowercase
    am/pm, weekday and month abbreviated to three letters, no leading zero on
    the day. Minutes are dropped when they are zero so the common case reads
    cleanly.
    """
    if isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        dt = value
    hour12 = dt.hour % 12 or 12
    suffix = "am" if dt.hour < 12 else "pm"
    minute_part = "" if dt.minute == 0 else f":{dt.minute:02d}"
    weekday = dt.strftime("%a")
    month = dt.strftime("%b")
    return f"{weekday} {month} {dt.day} at {hour12}{minute_part}{suffix}"
