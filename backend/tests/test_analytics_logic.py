"""
Unit tests for app/services/analytics_logic.py.

Pure functions only — no database, no HTTP — so these run anywhere:

    pytest tests/test_analytics_logic.py -v

The most important property tested here: with no rows, every function
returns zeros / None / empty, never placeholder figures.
"""

from datetime import date, datetime, timedelta, timezone

from app.services import analytics_logic as logic

UTC = timezone.utc
# Wednesday 2026-09-16, 12:00 UTC. Its Monday is 2026-09-14.
NOW = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)


def _dt(day: int, hour: int = 12, minute: int = 0, month: int = 9) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


class TestWeeks:
    def test_week_start_is_monday(self):
        assert logic.week_start(date(2026, 9, 16)) == date(2026, 9, 14)
        assert logic.week_start(date(2026, 9, 14)) == date(2026, 9, 14)
        assert logic.week_start(date(2026, 9, 20)) == date(2026, 9, 14)

    def test_build_week_starts_oldest_first_ending_with_current_week(self):
        weeks = logic.build_week_starts(NOW.date(), 4)
        assert weeks == [date(2026, 8, 24), date(2026, 8, 31), date(2026, 9, 7), date(2026, 9, 14)]

    def test_build_week_starts_is_clamped(self):
        assert len(logic.build_week_starts(NOW.date(), 0)) == 1
        assert len(logic.build_week_starts(NOW.date(), 500)) == logic.MAX_INSIGHT_WEEKS


class TestEmptyInputsAreZeroNeverPlaceholders:
    def test_weekly_series_are_all_zero(self):
        weeks = logic.build_week_starts(NOW.date(), 4)
        assert logic.weekly_totals([], weeks) == [0.0, 0.0, 0.0, 0.0]
        assert logic.weekly_counts([], weeks) == [0, 0, 0, 0]

    def test_matching_time_has_no_average(self):
        weeks = logic.build_week_starts(NOW.date(), 4)
        weekly, overall, samples = logic.weekly_matching_time([], weeks)
        assert overall is None
        assert samples == 0
        assert all(point["avg_minutes"] is None and point["samples"] == 0 for point in weekly)

    def test_operation_summary_is_all_zero(self):
        weeks = logic.build_week_starts(NOW.date(), 4)
        summary = logic.summarize_operations([], weeks, NOW)
        assert summary["completion"] == {"completed": 0, "in_progress": 0, "failed": 0}
        assert summary["deadline"] == {"on_time": 0, "late": 0, "no_deadline": 0}
        assert all(w["completed"] == 0 and w["at_risk"] == 0 for w in summary["weekly"])

    def test_surplus_history_is_zero_filled_and_forecast_is_none(self):
        history = logic.surplus_history([], NOW)
        assert len(history) == logic.HISTORY_DAYS
        assert all(day["quantity"] == 0 for day in history)
        assert logic.predict_surplus_window([], NOW) is None


class TestWeeklySeries:
    def test_totals_are_bucketed_by_utc_monday_and_outside_rows_ignored(self):
        weeks = logic.build_week_starts(NOW.date(), 2)  # 2026-09-07 and 2026-09-14
        rows = [
            (_dt(8), 10),  # week of 09-07
            (_dt(13, 23, 59), 5),  # Sunday, still week of 09-07
            (_dt(14, 0, 0), 7),  # Monday 00:00 UTC, week of 09-14
            (_dt(1), 999),  # before the window
        ]
        assert logic.weekly_totals(rows, weeks) == [15.0, 7.0]
        assert logic.weekly_counts([r[0] for r in rows], weeks) == [2, 1]

    def test_matching_time_averages_minutes_per_week(self):
        weeks = logic.build_week_starts(NOW.date(), 2)
        rows = [
            (_dt(8, 10, 0), _dt(8, 10, 10)),  # 10 min
            (_dt(9, 10, 0), _dt(9, 10, 30)),  # 30 min
            (_dt(15, 9, 0), _dt(15, 9, 5)),  # 5 min, next week
        ]
        weekly, overall, samples = logic.weekly_matching_time(rows, weeks)
        assert weekly[0]["avg_minutes"] == 20.0 and weekly[0]["samples"] == 2
        assert weekly[1]["avg_minutes"] == 5.0 and weekly[1]["samples"] == 1
        assert overall == 15.0
        assert samples == 3


class TestOperationSummary:
    WEEKS = logic.build_week_starts(NOW.date(), 2)

    def test_deadline_split_and_completion_counts(self):
        rows = [
            # on time: arrived at 11:00, deadline 12:00
            (_dt(8), "COMPLETED", _dt(8, 11), _dt(8, 11, 30), _dt(8, 12), None),
            # late: arrived 13:00, deadline 12:00
            (_dt(9), "DELIVERED", _dt(9, 13), None, _dt(9, 12), None),
            # falls back to the resource expiry when the request has no deadline
            (_dt(10), "COMPLETED", _dt(10, 9), None, None, _dt(10, 10)),
            # arrived, but no deadline anywhere
            (_dt(10), "COMPLETED", _dt(10, 9), None, None, None),
            # still open
            (_dt(15), "IN_TRANSIT", None, None, _dt(20), None),
            (_dt(15), "PLANNED", None, None, None, None),
            # failed
            (_dt(15), "FAILED", None, None, _dt(20), None),
        ]
        summary = logic.summarize_operations(rows, self.WEEKS, NOW)
        assert summary["completion"] == {"completed": 4, "in_progress": 2, "failed": 1}
        assert summary["deadline"] == {"on_time": 2, "late": 1, "no_deadline": 1}

    def test_weekly_completed_vs_at_risk(self):
        rows = [
            (_dt(8), "COMPLETED", _dt(8, 11), None, _dt(8, 12), None),  # completed
            (_dt(9), "DELIVERED", _dt(9, 13), None, _dt(9, 12), None),  # arrived late -> at risk
            (_dt(10), "FAILED", None, None, None, None),  # failed -> at risk
            (_dt(11), "IN_TRANSIT", None, None, _dt(12), None),  # open, deadline passed -> at risk
            (_dt(11), "IN_TRANSIT", None, None, _dt(30), None),  # open, not due -> neither
            (_dt(15), "COMPLETED", None, None, None, None),  # done, no timestamps -> completed
        ]
        weekly = logic.summarize_operations(rows, self.WEEKS, NOW)["weekly"]
        assert (weekly[0]["completed"], weekly[0]["at_risk"]) == (1, 3)
        assert (weekly[1]["completed"], weekly[1]["at_risk"]) == (1, 0)

    def test_naive_datetimes_are_treated_as_utc(self):
        naive = datetime(2026, 9, 8, 10, 0)
        rows = [(naive, "COMPLETED", naive, None, naive + timedelta(hours=1), None)]
        summary = logic.summarize_operations(rows, self.WEEKS, NOW)
        assert summary["deadline"]["on_time"] == 1


class TestSurplusForecast:
    def _rows_at_hour(self, hour: int, quantities: list[float], unit="meals"):
        """One surplus row per day at `hour` UTC, on consecutive days ending 2026-09-16."""
        rows = []
        for i, quantity in enumerate(reversed(quantities)):
            day = NOW.date() - timedelta(days=i)
            rows.append((datetime(day.year, day.month, day.day, hour, 15, tzinfo=UTC), quantity, unit))
        return rows

    def test_history_is_last_seven_local_days_zero_filled(self):
        rows = [(_dt(16, 8), 40, "meals"), (_dt(16, 20), 20, "meals"), (_dt(14, 9), 30, "meals")]
        history = logic.surplus_history(rows, NOW)
        assert [d["day"] for d in history][-1] == date(2026, 9, 16)
        assert history[-1]["quantity"] == 60.0
        assert history[-3]["quantity"] == 30.0  # 09-14
        assert history[-2]["quantity"] == 0.0  # 09-15
        assert [d["label"] for d in history][-3:] == ["Mon", "Tue", "Wed"]

    def test_history_respects_timezone_offset(self):
        # 22:00 UTC on the 15th is already 03:30 on the 16th in IST (+330 min).
        rows = [(_dt(15, 22), 10, "meals")]
        history = logic.surplus_history(rows, NOW, tz_offset_minutes=330)
        by_day = {d["day"]: d["quantity"] for d in history}
        assert by_day[date(2026, 9, 16)] == 10.0
        assert by_day[date(2026, 9, 15)] == 0.0

    def test_no_forecast_below_minimum_days(self):
        rows = self._rows_at_hour(22, [80, 100])  # only 2 days
        assert logic.predict_surplus_window(rows, NOW) is None

    def test_forecast_picks_the_busiest_eligible_hour_and_uses_observed_range(self):
        busy = self._rows_at_hour(22, [80, 100, 90, 85])
        quiet = self._rows_at_hour(14, [5, 6, 7, 8])
        forecast = logic.predict_surplus_window(busy + quiet, NOW)
        assert forecast is not None
        assert (forecast["start_hour"], forecast["end_hour"]) == (22, 23)
        assert (forecast["low"], forecast["high"]) == (80.0, 100.0)
        assert forecast["unit"] == "meals"
        assert forecast["days_with_surplus"] == 4

    def test_forecast_hour_is_local_time(self):
        rows = self._rows_at_hour(17, [50, 60, 55])  # 17:15 UTC == 22:45 IST
        forecast = logic.predict_surplus_window(rows, NOW, tz_offset_minutes=330)
        assert forecast["start_hour"] == 22

    def test_ineligible_hour_with_big_totals_does_not_beat_eligible_one(self):
        rows = self._rows_at_hour(22, [10, 10, 10]) + [(_dt(16, 5), 5000, "meals")]
        forecast = logic.predict_surplus_window(rows, NOW)
        assert forecast["start_hour"] == 22

    def test_mixed_units_fall_back_to_units(self):
        rows = self._rows_at_hour(22, [10, 10, 10], unit="meals")
        rows[0] = (rows[0][0], rows[0][1], "kg")
        assert logic.predict_surplus_window(rows, NOW)["unit"] == "units"

    def test_rows_outside_the_window_are_ignored(self):
        old = [(NOW - timedelta(days=60 + i), 100, "meals") for i in range(5)]
        assert logic.predict_surplus_window(old, NOW) is None

    def test_format_hour(self):
        assert logic.format_hour(0) == "12 AM"
        assert logic.format_hour(12) == "12 PM"
        assert logic.format_hour(22) == "10 PM"
        assert logic.format_hour(24) == "12 AM"
