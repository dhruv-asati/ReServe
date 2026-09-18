"""
Tests for POST /api/resources/{resource_id}/analyze.

Gemini itself is never called in this suite. `gemini_service.is_configured`
is monkeypatched to True (skipping the "no API key" guard) and
`gemini_service.call_gemini_model` — the one function in that module that
actually talks to Google — is monkeypatched to return a canned JSON
string. Everything else (prompt building, response parsing, Pydantic
validation against ResourceAnalysis, storage, ownership checks, error
handling) still runs for real, with no GEMINI_API_KEY or network access
needed.

Shared fixtures (db, client, make_user, make_resource, login_headers)
live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_resource_analysis.py -v
"""

import json
import uuid

from app.models.enums import ResourceType, UserRole
from app.services import gemini_service

from tests.conftest import login_headers, make_resource, make_user

VALID_FOOD_ANALYSIS = {
    "resource_category": "Perishable food",
    "resource_subtype": "Cooked meals",
    "extracted_quantity": {"value": 80, "unit": "meals", "matches_posted_quantity": True},
    "urgency_level": "HIGH",
    "rescue_window": {
        "recommended_pickup_within_hours": 3,
        "reasoning": "Cooked food held at room temperature degrades quickly.",
    },
    "important_attributes": ["contains dairy", "individually packaged"],
    "storage_requirements": "Keep refrigerated below 4C until pickup.",
    "eligibility_info": None,
    "warnings": ["Contains milk and wheat allergens."],
    "confidence_score": 0.86,
}

VALID_MEDICAL_ANALYSIS = {
    "resource_category": "Pharmaceutical",
    "resource_subtype": "Antibiotic",
    "extracted_quantity": {"value": 200, "unit": "units", "matches_posted_quantity": True},
    "urgency_level": "MEDIUM",
    "rescue_window": {
        "recommended_pickup_within_hours": 240,
        "reasoning": "Stock is near-expiry but does not expire for several weeks.",
    },
    "important_attributes": ["unopened boxes", "requires prescription"],
    "storage_requirements": "Store at room temperature, away from moisture.",
    "eligibility_info": "Restricted to licensed clinics or pharmacies.",
    "warnings": ["Verify batch has not been recalled before distribution."],
    "confidence_score": 0.78,
}


def _mock_gemini(monkeypatch, response_dict=None, raise_exc=None):
    monkeypatch.setattr(gemini_service, "is_configured", lambda: True)
    if raise_exc is not None:
        def _boom(prompt):
            raise raise_exc

        monkeypatch.setattr(gemini_service, "call_gemini_model", _boom)
    else:
        monkeypatch.setattr(gemini_service, "call_gemini_model", lambda prompt: json.dumps(response_dict))


class TestAnalyzeResource:
    def test_provider_can_analyze_food_resource(self, client, db, monkeypatch):
        _mock_gemini(monkeypatch, VALID_FOOD_ANALYSIS)
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 200, resp.text
        ai = resp.json()["data"]["ai_analysis"]
        assert ai["analysis"]["resource_category"] == "Perishable food"
        assert ai["analysis"]["confidence_score"] == 0.86
        assert ai["model"]
        assert ai["analyzed_at"]

    def test_provider_can_analyze_medical_resource(self, client, db, monkeypatch):
        _mock_gemini(monkeypatch, VALID_MEDICAL_ANALYSIS)
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(
            db,
            provider,
            resource_type=ResourceType.MEDICAL,
            title="200 units amoxicillin 500mg",
            quantity=200,
            unit="units",
            category="antibiotics",
            requires_medical_verification=True,
        )

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 200, resp.text
        analysis = resp.json()["data"]["ai_analysis"]["analysis"]
        assert analysis["resource_subtype"] == "Antibiotic"
        assert analysis["eligibility_info"] == "Restricted to licensed clinics or pharmacies."

    def test_analysis_can_be_re_run_and_overwrites_previous_result(self, client, db, monkeypatch):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        _mock_gemini(monkeypatch, VALID_FOOD_ANALYSIS)
        first = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)
        assert first.status_code == 200, first.text

        second_analysis = {**VALID_FOOD_ANALYSIS, "confidence_score": 0.42}
        _mock_gemini(monkeypatch, second_analysis)
        second = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert second.status_code == 200, second.text
        assert second.json()["data"]["ai_analysis"]["analysis"]["confidence_score"] == 0.42

    def test_analysis_never_changes_resource_status(self, client, db, monkeypatch):
        """Gemini analyzes and structures only — it must never move the
        resource toward allocation on its own."""
        _mock_gemini(monkeypatch, VALID_FOOD_ANALYSIS)
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "AVAILABLE"

    def test_other_provider_cannot_analyze_someone_elses_resource(self, client, db, monkeypatch):
        _mock_gemini(monkeypatch, VALID_FOOD_ANALYSIS)
        owner = make_user(db, role=UserRole.PROVIDER, email="owner@example.com")
        resource = make_resource(db, owner, resource_type=ResourceType.FOOD)

        other = make_user(db, role=UserRole.PROVIDER, email="other@example.com")
        headers = login_headers(client, other.email)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "NOT_RESOURCE_OWNER"

    def test_admin_can_analyze_any_resource(self, client, db, monkeypatch):
        _mock_gemini(monkeypatch, VALID_FOOD_ANALYSIS)
        owner = make_user(db, role=UserRole.PROVIDER, email="owner2@example.com")
        resource = make_resource(db, owner, resource_type=ResourceType.FOOD)

        admin = make_user(db, role=UserRole.ADMIN, email="admin@example.com")
        headers = login_headers(client, admin.email)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 200, resp.text

    def test_returns_404_for_unknown_resource(self, client, db, monkeypatch):
        _mock_gemini(monkeypatch, VALID_FOOD_ANALYSIS)
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/resources/{uuid.uuid4()}/analyze", headers=headers)

        assert resp.status_code == 404, resp.text

    def test_requires_authentication(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze")

        assert resp.status_code == 401, resp.text

    def test_returns_503_when_gemini_not_configured(self, client, db, monkeypatch):
        monkeypatch.setattr(gemini_service, "is_configured", lambda: False)
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 503, resp.text
        assert resp.json()["error"]["code"] == "AI_ANALYSIS_NOT_CONFIGURED"

    def test_returns_504_on_timeout(self, client, db, monkeypatch):
        class DeadlineExceeded(Exception):
            pass

        _mock_gemini(monkeypatch, raise_exc=DeadlineExceeded("timed out"))
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 504, resp.text
        assert resp.json()["error"]["code"] == "AI_ANALYSIS_TIMEOUT"

    def test_returns_502_on_generic_gemini_failure(self, client, db, monkeypatch):
        _mock_gemini(monkeypatch, raise_exc=RuntimeError("boom"))
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 502, resp.text
        assert resp.json()["error"]["code"] == "AI_ANALYSIS_FAILED"

    def test_returns_502_on_non_json_response(self, client, db, monkeypatch):
        monkeypatch.setattr(gemini_service, "is_configured", lambda: True)
        monkeypatch.setattr(gemini_service, "call_gemini_model", lambda prompt: "not json at all")
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 502, resp.text
        assert resp.json()["error"]["code"] == "AI_ANALYSIS_INVALID_RESPONSE"

    def test_returns_502_when_response_fails_schema_validation(self, client, db, monkeypatch):
        bad = {**VALID_FOOD_ANALYSIS, "confidence_score": 5.0}  # out of the 0..1 range
        _mock_gemini(monkeypatch, bad)
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 502, resp.text
        assert resp.json()["error"]["code"] == "AI_ANALYSIS_INVALID_RESPONSE"

    def test_handles_response_wrapped_in_markdown_fences(self, client, db, monkeypatch):
        """Defensive cleanup for a model that ignores JSON mode and wraps
        its answer in ```json ... ``` anyway."""
        monkeypatch.setattr(gemini_service, "is_configured", lambda: True)
        fenced = "```json\n" + json.dumps(VALID_FOOD_ANALYSIS) + "\n```"
        monkeypatch.setattr(gemini_service, "call_gemini_model", lambda prompt: fenced)
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)

        resp = client.post(f"/api/resources/{resource.id}/analyze", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["ai_analysis"]["analysis"]["resource_category"] == "Perishable food"
