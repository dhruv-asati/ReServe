"""
Integration tests for:

    GET  /api/analytics/insights
    GET  /api/analytics/surplus-forecast
    POST /api/analytics/surplus-alert

The point of these tests is the policy the Analytics page depends on: an
empty platform yields zeros / nulls (never demo figures), and the "notify
partners" action reports exactly how many real partners it notified.

Shared fixtures/helpers live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_analytics_insights.py -v
"""

from datetime import datetime, timedelta, timezone

from app.models.enums import UserRole
from app.models.notification import Notification
from app.services.notification_service import SURPLUS_ALERT_TITLE

from tests.conftest import login_headers, make_rescue_partner, make_resource, make_user


def _seed_surplus(db, provider, days: int = 3, hour: int = 22, quantity: float = 90):
    """`days` past days of FOOD surplus, all becoming available at `hour`:15 UTC."""
    base = datetime.now(timezone.utc).replace(hour=hour, minute=15, second=0, microsecond=0)
    for i in range(1, days + 1):
        make_resource(db, provider, available_time=base - timedelta(days=i), quantity=quantity + i)


def _post_alert(client, headers):
    return client.post("/api/analytics/surplus-alert", json={"tz_offset_minutes": 0}, headers=headers)


class TestInsights:
    def test_requires_authentication(self, db, client):
        assert client.get("/api/analytics/insights").status_code == 401

    def test_empty_platform_returns_zeros_and_nulls(self, db, client):
        user = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, user.email)

        resp = client.get("/api/analytics/insights", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["window_weeks"] == 4
        for key in ("supply_vs_demand", "allocations", "matching_time", "operation_outcomes"):
            assert len(data[key]) == 4
        assert all(w["supply"] == 0 and w["demand"] == 0 for w in data["supply_vs_demand"])
        assert all(w["successful"] == 0 and w["unsuccessful"] == 0 for w in data["allocations"])
        assert all(w["avg_minutes"] is None for w in data["matching_time"])
        assert data["avg_matching_minutes"] is None
        assert data["matching_samples"] == 0
        assert data["deadline_performance"] == {"on_time": 0, "late": 0, "no_deadline": 0}
        assert data["operation_completion"] == {"completed": 0, "in_progress": 0, "failed": 0}
        assert all(w["completed"] == 0 and w["at_risk"] == 0 for w in data["operation_outcomes"])

    def test_supply_counts_posted_resources_in_the_current_week(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        make_resource(db, provider, quantity=50)

        data = client.get("/api/analytics/insights", headers=headers).json()["data"]

        assert data["supply_vs_demand"][-1]["supply"] == 50
        assert sum(w["supply"] for w in data["supply_vs_demand"][:-1]) == 0

    def test_weeks_parameter_is_validated(self, db, client):
        user = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, user.email)
        assert client.get("/api/analytics/insights?weeks=0", headers=headers).status_code == 422
        assert client.get("/api/analytics/insights?weeks=13", headers=headers).status_code == 422
        resp = client.get("/api/analytics/insights?weeks=2", headers=headers)
        assert resp.json()["data"]["window_weeks"] == 2


class TestSurplusForecast:
    def test_empty_platform_has_no_prediction(self, db, client):
        user = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, user.email)

        resp = client.get("/api/analytics/surplus-forecast", headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["prediction"] is None
        assert len(data["history"]) == 7
        assert all(day["quantity"] == 0 for day in data["history"])

    def test_predicts_the_usual_hour_from_recorded_surplus(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        _seed_surplus(db, provider, days=3, hour=22, quantity=90)  # 91, 92, 93

        data = client.get("/api/analytics/surplus-forecast", headers=headers).json()["data"]

        prediction = data["prediction"]
        assert prediction is not None
        assert (prediction["start_hour"], prediction["end_hour"]) == (22, 23)
        assert (prediction["low"], prediction["high"]) == (91, 93)
        assert prediction["unit"] == "meals"
        assert prediction["days_with_surplus"] == 3
        assert data["unit"] == "meals"

    def test_too_little_history_gives_no_prediction(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        _seed_surplus(db, provider, days=2)

        data = client.get("/api/analytics/surplus-forecast", headers=headers).json()["data"]
        assert data["prediction"] is None


class TestSurplusAlert:
    def test_recipients_may_not_send_alerts(self, db, client):
        recipient = make_user(db, role=UserRole.RECIPIENT)
        headers = login_headers(client, recipient.email)
        assert _post_alert(client, headers).status_code == 403

    def test_no_forecast_means_409_and_nobody_is_notified(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        make_rescue_partner(db, partner_user)
        headers = login_headers(client, provider.email)

        resp = _post_alert(client, headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "NO_SURPLUS_FORECAST"
        assert db.query(Notification).count() == 0

    def test_with_no_partners_the_count_is_really_zero(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        _seed_surplus(db, provider)

        resp = _post_alert(client, headers)

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["partners_notified"] == 0
        assert data["eligible_partners"] == 0
        assert db.query(Notification).count() == 0

    def test_only_available_food_partners_are_notified_and_only_once_per_hour(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        _seed_surplus(db, provider)

        available = [make_user(db, role=UserRole.RESCUE_PARTNER) for _ in range(2)]
        for user in available:
            make_rescue_partner(db, user)
        busy = make_user(db, role=UserRole.RESCUE_PARTNER)
        make_rescue_partner(db, busy, is_available=False)
        medical_only = make_user(db, role=UserRole.RESCUE_PARTNER)
        make_rescue_partner(db, medical_only, accepts_food=False, accepts_medical=True)

        first = _post_alert(client, headers).json()["data"]
        assert first["partners_notified"] == 2
        assert first["eligible_partners"] == 2
        assert first["scope"] == "all_available"
        assert first["window_label"] == "10 PM – 11 PM"

        notified_ids = {n.user_id for n in db.query(Notification).filter_by(title=SURPLUS_ALERT_TITLE)}
        assert notified_ids == {user.id for user in available}

        second = _post_alert(client, headers).json()["data"]
        assert second["partners_notified"] == 0
        assert second["already_notified"] == 2
        assert db.query(Notification).count() == 2
