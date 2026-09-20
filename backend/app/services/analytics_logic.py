"""
Pure calculation logic for the Analytics page:

    GET  /api/analytics/insights
    GET  /api/analytics/surplus-forecast
    POST /api/analytics/surplus-alert

Nothing in here touches the database, FastAPI, or any other ReServe module
— it only turns plain rows into plain dicts/lists, exactly like
app/services/prediction_logic.py. app/services/analytics_service.py runs the
SELECTs and hands the rows to these functions, which keeps the maths
trivially testable (tests/test_analytics_logic.py needs no database).

Policy: NO placeholder numbers, ever. Every function returns zeros / None /
empty lists when the rows it is given are empty, and the frontend renders
those as empty states instead of charts.

Plain strings ("COMPLETED", ...) are used for statuses instead of importing
app.models.enums, so this module stays importable on its own (same
convention as prediction_logic.py).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

MIN_INSIGHT_WEEKS = 1
MAX_INSIGHT_WEEKS = 12
DEFAULT_INSIGHT_WEEKS = 4

# Surplus forecast: how many recent days feed the forecast, how many of the
# most recent days are drawn as the history chart, and how many distinct days
# an hour-of-day slot must have seen surplus on before we are willing to
# predict from it. Fewer than this and we say "not enough history" rather
# than build a range out of one or two data points.
FORECAST_WINDOW_DAYS = 28
HISTORY_DAYS = 7
MIN_DAYS_FOR_FORECAST = 3

# Operation statuses (mirror app.models.enums.OperationStatus).
_DONE = ("DELIVERED", "COMPLETED")
_IN_PROGRESS = ("PLANNED", "IN_TRANSIT")
_FAILED = ("FAILED",)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC and convert aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def week_start(day: date) -> date:
    """Monday of the week containing `day`."""
    return day - timedelta(days=day.weekday())


def build_week_starts(today: date, weeks: int) -> list[date]:
    """
    `weeks` Mondays (UTC), oldest first, ending with the current — still in
    progress — week. Always exactly `weeks` entries.
    """
    weeks = max(MIN_INSIGHT_WEEKS, min(MAX_INSIGHT_WEEKS, weeks))
    current = week_start(today)
    return [current - timedelta(weeks=weeks - 1 - i) for i in range(weeks)]


def _week_of(value: datetime) -> date:
    return week_start(as_utc(value).date())


# ---------------------------------------------------------------------------
# Weekly series
# ---------------------------------------------------------------------------


def weekly_totals(rows: Iterable[tuple[datetime, float]], week_starts: list[date]) -> list[float]:
    """Sum of `value` per week, aligned with `week_starts`. Rows outside the window are ignored."""
    totals = {w: 0.0 for w in week_starts}
    for when, value in rows:
        week = _week_of(when)
        if week in totals:
            totals[week] += float(value or 0)
    return [round(totals[w], 2) for w in week_starts]


def weekly_counts(whens: Iterable[datetime], week_starts: list[date]) -> list[int]:
    """Number of timestamps falling in each week, aligned with `week_starts`."""
    counts = {w: 0 for w in week_starts}
    for when in whens:
        week = _week_of(when)
        if week in counts:
            counts[week] += 1
    return [counts[w] for w in week_starts]


def weekly_matching_time(
    rows: Iterable[tuple[datetime, datetime]], week_starts: list[date]
) -> tuple[list[dict], Optional[float], int]:
    """
    Average minutes from a rescue request being created to its first
    allocation, per week of request creation.

    `rows` are (request_created_at, first_allocation_created_at). Weeks in
    which nothing was matched report `avg_minutes: None` (a gap in the line),
    never a made-up zero. Returns (weekly, overall_average, total_samples).
    """
    buckets: dict[date, list[float]] = defaultdict(list)
    for created_at, matched_at in rows:
        week = _week_of(created_at)
        if week not in week_starts:
            continue
        minutes = (as_utc(matched_at) - as_utc(created_at)).total_seconds() / 60.0
        buckets[week].append(max(minutes, 0.0))

    weekly = []
    all_minutes: list[float] = []
    for week in week_starts:
        samples = buckets.get(week, [])
        all_minutes.extend(samples)
        weekly.append(
            {
                "week_start": week,
                "avg_minutes": round(sum(samples) / len(samples), 2) if samples else None,
                "samples": len(samples),
            }
        )
    overall = round(sum(all_minutes) / len(all_minutes), 2) if all_minutes else None
    return weekly, overall, len(all_minutes)


# ---------------------------------------------------------------------------
# Operation outcomes
# ---------------------------------------------------------------------------


def summarize_operations(rows: Iterable[tuple], week_starts: list[date], now: datetime) -> dict:
    """
    Everything the operation-based charts need, from one pass over the rows.

    Each row is (created_at, status, delivered_at, completed_at,
    request_deadline, resource_expiry) with status a plain string. The
    deadline an operation is judged against is the rescue request's own
    deadline, falling back to the resource's expiry_time. When the operation
    reached the recipient is delivered_at, falling back to completed_at.

    Returns:
      completion    {completed, in_progress, failed}
                    completed = DELIVERED + COMPLETED (the goods arrived)
      deadline      {on_time, late, no_deadline} over operations that arrived
      weekly        one {week_start, completed, at_risk} per week, bucketed by
                    when the operation was created:
                      completed = arrived, and not after its deadline
                      at_risk   = FAILED, or arrived after its deadline, or
                                  still open although its deadline has passed
    """
    now = as_utc(now)
    completion = {"completed": 0, "in_progress": 0, "failed": 0}
    deadline_counts = {"on_time": 0, "late": 0, "no_deadline": 0}
    weekly = {w: {"week_start": w, "completed": 0, "at_risk": 0} for w in week_starts}

    for created_at, status, delivered_at, completed_at, request_deadline, resource_expiry in rows:
        finished = delivered_at or completed_at
        deadline = request_deadline or resource_expiry
        finished_utc = as_utc(finished) if finished else None
        deadline_utc = as_utc(deadline) if deadline else None

        if status in _DONE:
            completion["completed"] += 1
        elif status in _FAILED:
            completion["failed"] += 1
        elif status in _IN_PROGRESS:
            completion["in_progress"] += 1

        arrived_late = False
        if status in _DONE and finished_utc is not None:
            if deadline_utc is None:
                deadline_counts["no_deadline"] += 1
            elif finished_utc <= deadline_utc:
                deadline_counts["on_time"] += 1
            else:
                deadline_counts["late"] += 1
                arrived_late = True

        week = _week_of(created_at)
        bucket = weekly.get(week)
        if bucket is None:
            continue
        if status in _FAILED:
            bucket["at_risk"] += 1
        elif status in _DONE:
            bucket["at_risk" if arrived_late else "completed"] += 1
        elif status in _IN_PROGRESS and deadline_utc is not None and deadline_utc < now:
            bucket["at_risk"] += 1

    return {
        "completion": completion,
        "deadline": deadline_counts,
        "weekly": [weekly[w] for w in week_starts],
    }


# ---------------------------------------------------------------------------
# Surplus forecast
# ---------------------------------------------------------------------------


def clamp_offset(tz_offset_minutes: int) -> int:
    """UTC offsets on Earth span -12:00..+14:00; anything else is a bad client value."""
    return max(-14 * 60, min(14 * 60, int(tz_offset_minutes)))


def format_hour(hour: int) -> str:
    """0 -> '12 AM', 13 -> '1 PM'."""
    hour %= 24
    suffix = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12} {suffix}"


def _local(ts: datetime, offset_minutes: int) -> datetime:
    return as_utc(ts) + timedelta(minutes=offset_minutes)


def pick_unit(units: Iterable[Optional[str]]) -> str:
    """The single unit all rows share, else the neutral 'units' (mixed units are not converted)."""
    distinct = {u.strip().lower() for u in units if u and u.strip()}
    return distinct.pop() if len(distinct) == 1 else "units"


def surplus_history(
    rows: list[tuple[datetime, float, Optional[str]]],
    now: datetime,
    tz_offset_minutes: int = 0,
    days: int = HISTORY_DAYS,
) -> list[dict]:
    """
    Surplus quantity per local calendar day for the last `days` days ending
    today, oldest first, zero-filled. `rows` are (ready_at, quantity, unit).
    """
    offset = clamp_offset(tz_offset_minutes)
    today = _local(now, offset).date()
    totals = {today - timedelta(days=i): 0.0 for i in range(days)}
    for ready_at, quantity, _unit in rows:
        day = _local(ready_at, offset).date()
        if day in totals:
            totals[day] += float(quantity or 0)
    return [
        {"label": day.strftime("%a"), "day": day, "quantity": round(totals[day], 2)}
        for day in sorted(totals)
    ]


def history_unit(
    rows: list[tuple[datetime, float, Optional[str]]],
    now: datetime,
    tz_offset_minutes: int = 0,
    days: int = HISTORY_DAYS,
) -> str:
    """Unit for the history chart: the one unit shared by the rows it shows, else 'units'."""
    offset = clamp_offset(tz_offset_minutes)
    today = _local(now, offset).date()
    shown = {today - timedelta(days=i) for i in range(days)}
    return pick_unit(unit for ready_at, _qty, unit in rows if _local(ready_at, offset).date() in shown)


def predict_surplus_window(
    rows: list[tuple[datetime, float, Optional[str]]],
    now: datetime,
    tz_offset_minutes: int = 0,
    window_days: int = FORECAST_WINDOW_DAYS,
    min_days: int = MIN_DAYS_FOR_FORECAST,
) -> Optional[dict]:
    """
    The hour of the day (in the caller's local time) in which surplus food most
    reliably becomes available, and the range it has ranged over.

    Method — deliberately simple and explainable, not a trained model:
      1. Bucket every surplus row of the last `window_days` days by local
         (day, hour-of-day) and add up the quantity.
      2. An hour is eligible only if surplus appeared in it on at least
         `min_days` different days.
      3. Pick the eligible hour with the largest total quantity.
      4. The predicted range is the smallest and largest per-day total seen in
         that hour, over the days it had surplus.

    Returns None when no hour has enough history — the caller must show
    "not enough data yet", never a substitute figure.
    """
    offset = clamp_offset(tz_offset_minutes)
    today = _local(now, offset).date()
    first_day = today - timedelta(days=window_days - 1)

    per_hour: dict[int, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    units_by_hour: dict[int, list[Optional[str]]] = defaultdict(list)
    for ready_at, quantity, unit in rows:
        local = _local(ready_at, offset)
        if not (first_day <= local.date() <= today):
            continue
        per_hour[local.hour][local.date()] += float(quantity or 0)
        units_by_hour[local.hour].append(unit)

    best_hour: Optional[int] = None
    best_key: Optional[tuple[float, int]] = None
    for hour, per_day in per_hour.items():
        if len(per_day) < min_days:
            continue
        key = (sum(per_day.values()), len(per_day))
        if best_key is None or key > best_key:
            best_hour, best_key = hour, key

    if best_hour is None:
        return None

    per_day = per_hour[best_hour]
    return {
        "start_hour": best_hour,
        "end_hour": (best_hour + 1) % 24,
        "low": round(min(per_day.values()), 1),
        "high": round(max(per_day.values()), 1),
        "unit": pick_unit(units_by_hour[best_hour]),
        "days_with_surplus": len(per_day),
        "window_days": window_days,
    }
