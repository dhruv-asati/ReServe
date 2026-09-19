"""
Tests for GET /api/predictions.

TestPredictionLogic is pure (no DB rows are used) and covers the maths;
the remaining classes are integration tests against the real endpoint.
Shared fixtures live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_predictions.py -v
"""

from datetime import date, datetime, timedelta, timezone

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    FoodCategory,
    ResourceRequestStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.services import prediction_logic as logic

from tests.conftest import (
    login_headers,
    make_recipient,
    make_rescue_request,
    make_resource,
    make_resource_request,
    make_user,
)

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)  # a Saturday


def _weeks_ago(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(weeks=n)


class TestPredictionLogic:
    def test_resource_types_match_enum(self):
        assert set(logic.RESOURCE_TYPES) == {t.value for t in ResourceType}

    def test_week_start_is_monday(self):
        assert logic.week_start(date(2026, 9, 19)) == date(2026, 9, 14)
        assert logic.week_start(date(2026, 9, 14)) == date(2026, 9, 14)

    def test_window_is_whole_weeks_plus_partial_current(self):
        w = logic.build_window(date(2026, 9, 19), 90)
        assert w["weeks"] == 13
        assert len(w["week_starts"]) == 14
        assert w["week_starts"][-1] == date(2026, 9, 14)
        assert w["first_week"] == date(2026, 6, 15)

    def test_category_label_normalization(self):
        assert logic.category_label("  BAKERY ", None) == "Bakery"
        assert logic.category_label(None, "COOKED_MEALS") == "Cooked meals"
        assert logic.category_label("", None) == "Uncategorized"
        assert logic.category_label("   ", "DAIRY") == "Dairy"

    def test_rank_categories_merges_and_sorts(self):
        rows = [
            ("FOOD", "bakery", None, 2, 20),
            ("FOOD", "Bakery", None, 1, 10),  # same category, different case/source row
            ("FOOD", None, "COOKED_MEALS", 5, 100),
            ("MEDICAL", "antibiotics", None, 2, 8),
        ]
        ranked = logic.rank_categories(rows)
        assert [r["category"] for r in ranked] == ["Cooked meals", "Bakery", "Antibiotics"]
        assert ranked[1]["resource_count"] == 3
        assert ranked[1]["total_quantity"] == 30
        assert ranked[0]["share_percent"] == 50.0
        assert len(logic.rank_categories(rows, top_n=2)) == 2

    def test_classify_trend(self):
        assert logic.classify_trend(100, 150) == ("INCREASING", 50.0)
        assert logic.classify_trend(100, 50) == ("DECREASING", -50.0)
        assert logic.classify_trend(100, 105) == ("STABLE", 5.0)
        assert logic.classify_trend(0, 40) == ("INCREASING", None)
        assert logic.classify_trend(0, 0) == ("INSUFFICIENT_DATA", None)

    def test_demand_trend_uses_complete_weeks_only(self):
        w = logic.build_window(date(2026, 9, 19), 28)  # 4 complete weeks + partial
        ws = w["week_starts"]
        rows = [
            ("FOOD", ws[0], 1, 100),
            ("FOOD", ws[1], 1, 100),
            ("FOOD", ws[2], 1, 200),
            ("FOOD", ws[3], 1, 200),
            ("FOOD", ws[4], 1, 9999),  # partial current week: must not skew the trend
        ]
        food = logic.summarize_demand(rows, w)["by_resource_type"][0]
        assert food["earlier_period_quantity"] == 200
        assert food["recent_period_quantity"] == 400
        assert food["trend"] == "INCREASING"
        assert food["change_percent"] == 100.0
        assert food["requested_quantity"] == 10599  # totals still include everything

    def test_type_with_too_few_requests_is_insufficient(self):
        w = logic.build_window(date(2026, 9, 19), 28)
        summary = logic.summarize_demand([("FOOD", w["week_starts"][0], 2, 50)], w)
        assert summary["by_resource_type"][0]["trend"] == "INSUFFICIENT_DATA"

    def test_weekly_series_is_zero_filled(self):
        w = logic.build_window(date(2026, 9, 19), 28)
        summary = logic.summarize_supply([("FOOD", w["week_starts"][2], 3, 30)], w)
        assert len(summary["weekly"]) == 5
        assert [p["resource_count"] for p in summary["weekly"]] == [0, 0, 3, 0, 0]
        assert summary["weekly"][-1]["is_partial"] is True

    def test_insufficient_data_gives_demo_payload(self):
        payload = logic.build_payload(now=NOW, days=90, supply_rows=[], category_rows=[], demand_rows=[])
        assert payload["is_demo"] is True
        assert payload["data_source"] == "DEMO"
        assert payload["notice"].startswith("DEMO DATA")
        assert payload["data_sufficiency"]["is_sufficient"] is False
        assert payload["historical_totals"]["total_resources"] > 0
        assert payload["top_categories"]

    def test_demo_ignores_real_rows(self):
        w = logic.build_window(NOW.date(), 90)
        supply = [("FOOD", w["week_starts"][0], 2, 12345)]
        payload = logic.build_payload(now=NOW, days=90, supply_rows=supply, category_rows=[], demand_rows=[])
        assert payload["is_demo"] is True
        assert payload["data_sufficiency"]["resources_found"] == 2  # real count reported...
        assert payload["historical_totals"]["total_quantity"] != 12345  # ...but not used

    def test_sufficient_data_gives_real_payload(self):
        w = logic.build_window(NOW.date(), 90)
        ws = w["week_starts"]
        payload = logic.build_payload(
            now=NOW,
            days=90,
            supply_rows=[("FOOD", ws[3], 6, 60)],
            category_rows=[("FOOD", "bakery", None, 6, 60)],
            demand_rows=[("FOOD", ws[3], 5, 50)],
        )
        assert payload["is_demo"] is False
        assert payload["data_source"] == "DATABASE"
        assert payload["historical_totals"]["total_resources"] == 6
        assert payload["top_categories"][0]["category"] == "Bakery"

    def test_demo_works_for_every_valid_window_size(self):
        for days in (28, 29, 90, 365):
            payload = logic.build_payload(now=NOW, days=days, supply_rows=[], category_rows=[], demand_rows=[])
            assert len(payload["historical_totals"]["weekly"]) == logic.build_window(NOW.date(), days)["weeks"] + 1


class TestPredictionsEndpoint:
    def test_requires_authentication(self, db, client):
        assert client.get("/api/predictions").status_code == 401

    def test_empty_database_returns_labeled_demo(self, db, client):
        user = make_user(db, role=UserRole.RECIPIENT)
        resp = client.get("/api/predictions", headers=login_headers(client, user.email))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        data = body["data"]
        assert body["success"] is True
        assert data["is_demo"] is True
        assert data["data_source"] == "DEMO"
        assert "DEMO" in data["notice"]
        assert data["data_sufficiency"]["resources_found"] == 0
        assert data["historical_totals"]["by_resource_type"]
        assert data["top_categories"]
        assert data["demand_trends"]["by_resource_type"]

    def test_days_out_of_range_is_rejected(self, db, client):
        user = make_user(db)
        headers = login_headers(client, user.email)
        assert client.get("/api/predictions?days=7", headers=headers).status_code == 422
        assert client.get("/api/predictions?days=1000", headers=headers).status_code == 422
        assert client.get("/api/predictions?days=60", headers=headers).status_code == 200

    def test_real_data_is_used_when_sufficient(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        recipient = make_recipient(db, make_user(db, role=UserRole.RECIPIENT))
        headers = login_headers(client, provider.email)

        # 6 resources: 4 bakery (mixed case/whitespace), 2 antibiotics.
        for i, cat in enumerate(["Bakery", "bakery", " BAKERY ", "bakery"]):
            make_resource(db, provider, quantity=10, category=cat, created_at=_weeks_ago(1 + i))
        for i in range(2):
            make_resource(
                db, provider, resource_type=ResourceType.MEDICAL, quantity=5, category="Antibiotics",
                created_at=_weeks_ago(2 + i),
            )
        # Excluded: cancelled, and older than the 90-day window.
        make_resource(db, provider, status=ResourceStatus.CANCELLED, quantity=1000)
        make_resource(db, provider, quantity=1000, created_at=_weeks_ago(30))

        # Demand: FOOD requests rising over time, MEDICAL too sparse for a trend.
        for weeks_ago, qty in [(11, 10), (10, 10), (2, 40), (1, 40), (3, 40)]:
            make_resource_request(db, recipient, requested_quantity=qty, created_at=_weeks_ago(weeks_ago))
        make_resource_request(
            db, recipient, resource_type=ResourceType.MEDICAL, requested_quantity=7, created_at=_weeks_ago(2)
        )
        make_resource_request(
            db, recipient, status=ResourceRequestStatus.CANCELLED, requested_quantity=5000
        )

        resp = client.get("/api/predictions", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["is_demo"] is False
        assert data["data_source"] == "DATABASE"
        assert data["data_sufficiency"]["is_sufficient"] is True

        totals = data["historical_totals"]
        assert totals["total_resources"] == 6
        assert totals["total_quantity"] == 4 * 10 + 2 * 5
        by_type = {t["resource_type"]: t for t in totals["by_resource_type"]}
        assert by_type["FOOD"]["resource_count"] == 4
        assert by_type["MEDICAL"]["total_quantity"] == 10
        assert sum(p["resource_count"] for p in totals["weekly"]) == 6

        top = data["top_categories"]
        assert top[0]["category"] == "Bakery"
        assert top[0]["resource_count"] == 4
        assert top[1]["category"] == "Antibiotics"
        assert top[0]["share_percent"] == round(4 / 6 * 100, 1)

        demand = data["demand_trends"]
        assert demand["total_requests"] == 6
        trends = {t["resource_type"]: t for t in demand["by_resource_type"]}
        assert trends["FOOD"]["trend"] == "INCREASING"
        assert trends["FOOD"]["requested_quantity"] == 140
        assert trends["MEDICAL"]["trend"] == "INSUFFICIENT_DATA"

    def test_food_category_enum_used_when_free_text_category_missing(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        recipient = make_recipient(db, make_user(db, role=UserRole.RECIPIENT))
        headers = login_headers(client, provider.email)
        for _ in range(5):
            make_resource(db, provider, food_category=FoodCategory.COOKED_MEALS)
        for _ in range(5):
            make_resource_request(db, recipient)

        data = client.get("/api/predictions", headers=headers).json()["data"]
        assert data["is_demo"] is False
        assert data["top_categories"][0]["category"] == "Cooked meals"


class TestPredictionsAreReadOnly:
    def test_does_not_change_resources_or_allocations(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        recipient = make_recipient(db, make_user(db, role=UserRole.RECIPIENT))
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, status=ResourceStatus.MATCHING)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        db.add(Allocation(
            rescue_request_id=rescue_request.id, recipient_id=recipient.id,
            allocated_quantity=10, status=AllocationStatus.PENDING,
        ))
        db.commit()

        def snapshot():
            db.expire_all()
            return (
                db.query(Allocation).count(),
                [(a.status, float(a.allocated_quantity)) for a in db.query(Allocation).all()],
                db.query(type(resource)).one().status,
            )

        before = snapshot()
        assert client.get("/api/predictions", headers=headers).status_code == 200
        assert snapshot() == before

    def test_service_does_not_import_matching_or_allocation(self):
        import app.services.prediction_logic as pl
        import app.services.prediction_service as ps

        for module in (pl, ps):
            source = open(module.__file__).read()
            for forbidden in ("matching_engine", "matching_service", "allocation_service", "reallocation_service"):
                assert f"import {forbidden}" not in source and f"{forbidden} import" not in source
