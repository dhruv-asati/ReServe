"""
Pure calculation logic for GET /api/predictions.

Nothing in here touches the database, FastAPI, or any other ReServe
module — it only turns plain aggregate rows into a plain dict. That keeps
the "basic prediction" maths trivially testable, and guarantees by
construction that this feature cannot influence matching or allocation:
it has no way to read or write anything else.

Row shapes (all produced by app/services/prediction_service.py):

    supply_rows    (resource_type, week_start, resource_count, total_quantity)
    category_rows  (resource_type, category_text, food_category, resource_count, total_quantity)
    demand_rows    (resource_type, week_start, request_count, requested_quantity)

`week_start` is the Monday (UTC) of the week the rows were created in.
`resource_type` is the plain string "FOOD" or "MEDICAL".

The "prediction" is deliberately simple and explainable: a demand trend is
the requested quantity in the later half of the window compared with the
earlier half, over *complete* weeks only (the in-progress current week
would otherwise always look like a drop).
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

RESOURCE_TYPES = ("FOOD", "MEDICAL")  # mirrors app.models.enums.ResourceType

# A real (database-backed) response needs at least this much recorded
# activity in the window; otherwise a clearly labeled demo response is
# returned instead of trends drawn from a handful of rows.
MIN_RESOURCES_FOR_REAL_DATA = 5
MIN_REQUESTS_FOR_REAL_DATA = 5

# Per-type: fewer requests than this and that type's trend is reported as
# INSUFFICIENT_DATA rather than a percentage built on one or two rows.
MIN_REQUESTS_PER_TYPE_FOR_TREND = 3

# Changes within +/- this many percent are reported as STABLE.
STABLE_BAND_PERCENT = 10.0

DEFAULT_TOP_CATEGORIES = 5

TREND_INCREASING = "INCREASING"
TREND_DECREASING = "DECREASING"
TREND_STABLE = "STABLE"
TREND_INSUFFICIENT = "INSUFFICIENT_DATA"


# --------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------


def week_start(d: date) -> date:
    """Monday of the week containing `d`."""
    return d - timedelta(days=d.weekday())


def build_window(today: date, days: int) -> dict:
    """
    The analysis window is whole weeks: `weeks` complete weeks ending at
    the start of the current week, plus the current (partial) week.
    """
    weeks = max(1, math.ceil(days / 7))
    current_week = week_start(today)
    first_week = current_week - timedelta(weeks=weeks)
    week_starts = [first_week + timedelta(weeks=i) for i in range(weeks + 1)]
    return {
        "weeks": weeks,
        "first_week": first_week,
        "current_week": current_week,
        "week_starts": week_starts,  # last entry is the partial current week
    }


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------


def category_label(category_text: str | None, food_category: str | None) -> str:
    """
    Human-readable, case-insensitive category name. Prefers the free-text
    `category`, falls back to the FOOD-only `food_category` enum value,
    then to "Uncategorized".
    """
    text = (category_text or "").strip()
    if not text and food_category:
        text = food_category.replace("_", " ")
    if not text:
        return "Uncategorized"
    text = text.lower()
    return text[0].upper() + text[1:]


def rank_categories(category_rows, top_n: int = DEFAULT_TOP_CATEGORIES) -> list[dict]:
    merged: dict[tuple[str, str], list[float]] = {}
    for resource_type, category_text, food_category, count, quantity in category_rows:
        key = (category_label(category_text, food_category), resource_type)
        entry = merged.setdefault(key, [0, 0.0])
        entry[0] += int(count)
        entry[1] += float(quantity)

    grand_total = sum(v[0] for v in merged.values())
    ranked = sorted(merged.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0][0], kv[0][1]))

    return [
        {
            "category": label,
            "resource_type": resource_type,
            "resource_count": int(count),
            "total_quantity": round(quantity, 2),
            "share_percent": round(count / grand_total * 100, 1) if grand_total else 0.0,
        }
        for (label, resource_type), (count, quantity) in ranked[:top_n]
    ]


# --------------------------------------------------------------------------
# Trends
# --------------------------------------------------------------------------


def classify_trend(earlier: float, recent: float) -> tuple[str, float | None]:
    """Returns (trend, change_percent). change_percent is None when it
    can't be expressed as a percentage (nothing in the earlier half)."""
    if earlier <= 0 and recent <= 0:
        return TREND_INSUFFICIENT, None
    if earlier <= 0:
        return TREND_INCREASING, None
    change = (recent - earlier) / earlier * 100
    if change >= STABLE_BAND_PERCENT:
        trend = TREND_INCREASING
    elif change <= -STABLE_BAND_PERCENT:
        trend = TREND_DECREASING
    else:
        trend = TREND_STABLE
    return trend, round(change, 1)


# --------------------------------------------------------------------------
# Summaries
# --------------------------------------------------------------------------


def _weekly(rows_by_key: dict, week_starts: list[date], current_week: date, keys: tuple[str, str]):
    count_key, qty_key = keys
    series = []
    for ws in week_starts:
        count, qty = rows_by_key.get(ws, (0, 0.0))
        series.append(
            {
                "period_start": ws,
                "is_partial": ws == current_week,
                count_key: int(count),
                qty_key: round(float(qty), 2),
            }
        )
    return series


def summarize_supply(supply_rows, window: dict) -> dict:
    per_type = {t: [0, 0.0] for t in RESOURCE_TYPES}
    per_week: dict[date, list[float]] = {}
    for resource_type, ws, count, quantity in supply_rows:
        if resource_type in per_type:
            per_type[resource_type][0] += int(count)
            per_type[resource_type][1] += float(quantity)
        entry = per_week.setdefault(ws, [0, 0.0])
        entry[0] += int(count)
        entry[1] += float(quantity)

    return {
        "total_resources": sum(v[0] for v in per_type.values()),
        "total_quantity": round(sum(v[1] for v in per_type.values()), 2),
        "by_resource_type": [
            {"resource_type": t, "resource_count": per_type[t][0], "total_quantity": round(per_type[t][1], 2)}
            for t in RESOURCE_TYPES
        ],
        "weekly": _weekly(
            {k: tuple(v) for k, v in per_week.items()},
            window["week_starts"],
            window["current_week"],
            ("resource_count", "total_quantity"),
        ),
    }


def summarize_demand(demand_rows, window: dict) -> dict:
    week_starts = window["week_starts"]
    complete_weeks = week_starts[:-1]  # trends ignore the partial current week
    split = len(complete_weeks) // 2
    earlier_weeks, recent_weeks = set(complete_weeks[:split]), set(complete_weeks[split:])

    per_type = {t: {"count": 0, "qty": 0.0, "earlier": 0.0, "recent": 0.0} for t in RESOURCE_TYPES}
    per_week: dict[date, list[float]] = {}
    for resource_type, ws, count, quantity in demand_rows:
        quantity = float(quantity)
        if resource_type in per_type:
            t = per_type[resource_type]
            t["count"] += int(count)
            t["qty"] += quantity
            if ws in earlier_weeks:
                t["earlier"] += quantity
            elif ws in recent_weeks:
                t["recent"] += quantity
        entry = per_week.setdefault(ws, [0, 0.0])
        entry[0] += int(count)
        entry[1] += quantity

    by_type = []
    for resource_type in RESOURCE_TYPES:
        t = per_type[resource_type]
        if t["count"] < MIN_REQUESTS_PER_TYPE_FOR_TREND:
            trend, change = TREND_INSUFFICIENT, None
        else:
            trend, change = classify_trend(t["earlier"], t["recent"])
        by_type.append(
            {
                "resource_type": resource_type,
                "request_count": t["count"],
                "requested_quantity": round(t["qty"], 2),
                "earlier_period_quantity": round(t["earlier"], 2),
                "recent_period_quantity": round(t["recent"], 2),
                "change_percent": change,
                "trend": trend,
            }
        )

    return {
        "total_requests": sum(t["count"] for t in per_type.values()),
        "total_requested_quantity": round(sum(t["qty"] for t in per_type.values()), 2),
        "by_resource_type": by_type,
        "weekly": _weekly(
            {k: tuple(v) for k, v in per_week.items()},
            week_starts,
            window["current_week"],
            ("request_count", "requested_quantity"),
        ),
    }


# --------------------------------------------------------------------------
# Demo data
# --------------------------------------------------------------------------
# Fixed, hand-written placeholder figures. They are NEVER derived from
# database rows, so they can't be mistaken for (or leak) real activity.

_DEMO_SUPPLY_COUNTS = {"FOOD": [6, 8, 7, 9, 10, 9, 11, 12], "MEDICAL": [2, 3, 2, 3, 4, 3, 4, 4]}
_DEMO_SUPPLY_UNIT_QTY = {"FOOD": 40.0, "MEDICAL": 25.0}
_DEMO_DEMAND_COUNTS = {"FOOD": [4, 5, 5, 7, 8, 9, 10, 11], "MEDICAL": [3, 3, 4, 3, 3, 4, 3, 3]}
_DEMO_DEMAND_UNIT_QTY = {"FOOD": 30.0, "MEDICAL": 15.0}
_DEMO_CATEGORY_ROWS = [
    ("FOOD", "Cooked meals", None, 34, 1360.0),
    ("FOOD", "Bakery", None, 17, 510.0),
    ("FOOD", "Raw produce", None, 12, 480.0),
    ("MEDICAL", "Antibiotics", None, 9, 225.0),
    ("MEDICAL", "Intravenous fluids", None, 6, 150.0),
]


def _demo_rows(window: dict):
    """Cycle the fixed demo patterns across however many weeks the window has."""
    week_starts = window["week_starts"]
    supply, demand = [], []
    for i, ws in enumerate(week_starts):
        for t in RESOURCE_TYPES:
            s = _DEMO_SUPPLY_COUNTS[t]
            d = _DEMO_DEMAND_COUNTS[t]
            s_count, d_count = s[i % len(s)], d[i % len(d)]
            supply.append((t, ws, s_count, s_count * _DEMO_SUPPLY_UNIT_QTY[t]))
            demand.append((t, ws, d_count, d_count * _DEMO_DEMAND_UNIT_QTY[t]))
    return supply, demand


# --------------------------------------------------------------------------
# Top-level assembly
# --------------------------------------------------------------------------


def build_payload(
    *,
    now: datetime,
    days: int,
    supply_rows,
    category_rows,
    demand_rows,
) -> dict:
    """
    Decides real vs demo and assembles the full response payload as a
    plain dict (validated into PredictionsData by the service layer).
    """
    window = build_window(now.date(), days)

    real_supply = summarize_supply(supply_rows, window)
    real_demand = summarize_demand(demand_rows, window)
    resources_found = real_supply["total_resources"]
    requests_found = real_demand["total_requests"]

    is_sufficient = (
        resources_found >= MIN_RESOURCES_FOR_REAL_DATA and requests_found >= MIN_REQUESTS_FOR_REAL_DATA
    )

    if is_sufficient:
        is_demo = False
        supply, categories, demand = real_supply, rank_categories(category_rows), real_demand
        notice = (
            f"Based on resources and resource requests recorded in the ReServe database since "
            f"{window['first_week'].isoformat()} (whole weeks; the current week is partial). "
            "Trends compare requested quantity in the later half of the window with the earlier "
            "half — a simple indicator, not a statistical forecast. Quantities are summed as "
            "recorded, so mixed units (e.g. meals and kg) are added together. Read-only: this "
            "endpoint does not influence matching or allocation."
        )
    else:
        is_demo = True
        demo_supply_rows, demo_demand_rows = _demo_rows(window)
        supply = summarize_supply(demo_supply_rows, window)
        categories = rank_categories(_DEMO_CATEGORY_ROWS)
        demand = summarize_demand(demo_demand_rows, window)
        notice = (
            f"DEMO DATA — NOT FROM YOUR DATABASE. Not enough recorded activity yet for a real "
            f"prediction (found {resources_found} resource(s) and {requests_found} request(s) in "
            f"the window; need at least {MIN_RESOURCES_FOR_REAL_DATA} and {MIN_REQUESTS_FOR_REAL_DATA}). "
            "Every figure below is a fixed, illustrative placeholder. Read-only: this endpoint "
            "does not influence matching or allocation."
        )

    return {
        "is_demo": is_demo,
        "data_source": "DEMO" if is_demo else "DATABASE",
        "notice": notice,
        "window_days": days,
        "window_start": window["first_week"],
        "generated_at": now,
        "data_sufficiency": {
            "is_sufficient": is_sufficient,
            "resources_found": resources_found,
            "resources_required": MIN_RESOURCES_FOR_REAL_DATA,
            "requests_found": requests_found,
            "requests_required": MIN_REQUESTS_FOR_REAL_DATA,
        },
        "historical_totals": supply,
        "top_categories": categories,
        "demand_trends": demand,
    }
