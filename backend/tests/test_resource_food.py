"""
Tests for the food-specific Resource fields: food_category, is_vegetarian,
preparation_time, allergen_info, storage_requirements, packaging_info.

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource) live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_resource_food.py -v
"""

from datetime import datetime, timedelta, timezone

from app.models.enums import ResourceType, UserRole

from tests.conftest import login_headers, make_resource, make_user

BASE_TIME = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


def _food_payload(**overrides) -> dict:
    payload = {
        "title": "80 vegetarian meals",
        "resource_type": "FOOD",
        "quantity": 80,
        "unit": "meals",
        "location_address": "Grand Plaza Hotel, MG Road, Bengaluru",
        "food_category": "COOKED_MEALS",
        "is_vegetarian": True,
        "preparation_time": BASE_TIME.isoformat(),
        "allergen_info": ["MILK", "WHEAT_GLUTEN"],
        "storage_requirements": "REFRIGERATED",
        "packaging_info": "Sealed aluminum trays, 10 meals per tray.",
    }
    payload.update(overrides)
    return payload


class TestCreateFoodResource:
    def test_create_food_resource_with_all_food_fields(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/resources", headers=headers, json=_food_payload())

        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["food_category"] == "COOKED_MEALS"
        assert data["is_vegetarian"] is True
        assert data["allergen_info"] == ["MILK", "WHEAT_GLUTEN"]
        assert data["storage_requirements"] == "REFRIGERATED"
        assert data["packaging_info"] == "Sealed aluminum trays, 10 meals per tray."
        assert data["preparation_time"] is not None

    def test_food_fields_are_optional(self, client, db):
        """Creating a FOOD resource without any food-specific fields still
        works — they're all nullable, so existing clients aren't broken."""
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "50 sandwiches",
                "resource_type": "FOOD",
                "quantity": 50,
                "unit": "sandwiches",
                "location_address": "Test Kitchen, Bengaluru",
            },
        )

        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["food_category"] is None
        assert data["is_vegetarian"] is None
        assert data["allergen_info"] is None
        assert data["storage_requirements"] is None
        assert data["packaging_info"] is None

    def test_allergen_info_none_alone_is_valid(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/resources", headers=headers, json=_food_payload(allergen_info=["NONE"]))

        assert resp.status_code == 201, resp.text
        assert resp.json()["data"]["allergen_info"] == ["NONE"]


class TestFoodFieldValidation:
    def test_medical_resource_rejects_food_category(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "200 units amoxicillin",
                "resource_type": "MEDICAL",
                "quantity": 200,
                "unit": "units",
                "location_address": "City Pharmacy, Bengaluru",
                "food_category": "COOKED_MEALS",
            },
        )

        assert resp.status_code == 422, resp.text

    def test_medical_resource_rejects_is_vegetarian(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "200 units amoxicillin",
                "resource_type": "MEDICAL",
                "quantity": 200,
                "unit": "units",
                "location_address": "City Pharmacy, Bengaluru",
                "is_vegetarian": True,
            },
        )

        assert resp.status_code == 422, resp.text

    def test_medical_resource_rejects_packaging_info(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "200 units amoxicillin",
                "resource_type": "MEDICAL",
                "quantity": 200,
                "unit": "units",
                "location_address": "City Pharmacy, Bengaluru",
                "packaging_info": "blister packs",
            },
        )

        assert resp.status_code == 422, resp.text

    def test_medical_resource_with_no_food_fields_is_fine(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "200 units amoxicillin",
                "resource_type": "MEDICAL",
                "quantity": 200,
                "unit": "units",
                "location_address": "City Pharmacy, Bengaluru",
            },
        )

        assert resp.status_code == 201, resp.text

    def test_invalid_food_category_enum_value_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources", headers=headers, json=_food_payload(food_category="NOT_A_REAL_CATEGORY")
        )

        assert resp.status_code == 422

    def test_invalid_allergen_enum_value_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/resources", headers=headers, json=_food_payload(allergen_info=["GLUTEN_FREE_LOL"]))

        assert resp.status_code == 422

    def test_allergen_none_combined_with_other_allergen_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/resources", headers=headers, json=_food_payload(allergen_info=["NONE", "MILK"]))

        assert resp.status_code == 422

    def test_duplicate_allergen_entries_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/resources", headers=headers, json=_food_payload(allergen_info=["MILK", "MILK"]))

        assert resp.status_code == 422

    def test_invalid_storage_requirement_enum_value_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources", headers=headers, json=_food_payload(storage_requirements="LUKEWARM")
        )

        assert resp.status_code == 422

    def test_preparation_time_after_available_time_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json=_food_payload(
                preparation_time=(BASE_TIME + timedelta(hours=2)).isoformat(),
                available_time=BASE_TIME.isoformat(),
                expiry_time=(BASE_TIME + timedelta(hours=6)).isoformat(),
            ),
        )

        assert resp.status_code == 422

    def test_preparation_time_after_expiry_time_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json=_food_payload(
                preparation_time=(BASE_TIME + timedelta(hours=10)).isoformat(),
                expiry_time=(BASE_TIME + timedelta(hours=6)).isoformat(),
            ),
        )

        assert resp.status_code == 422

    def test_preparation_time_before_available_and_expiry_is_valid(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/resources",
            headers=headers,
            json=_food_payload(
                preparation_time=BASE_TIME.isoformat(),
                available_time=(BASE_TIME + timedelta(hours=1)).isoformat(),
                expiry_time=(BASE_TIME + timedelta(hours=6)).isoformat(),
            ),
        )

        assert resp.status_code == 201, resp.text


class TestUpdateFoodResource:
    def test_update_food_fields_on_existing_food_resource(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)
        headers = login_headers(client, provider.email)

        resp = client.put(
            f"/api/resources/{resource.id}",
            headers=headers,
            json={"food_category": "BAKERY", "is_vegetarian": False, "allergen_info": ["EGGS"]},
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["food_category"] == "BAKERY"
        assert data["is_vegetarian"] is False
        assert data["allergen_info"] == ["EGGS"]

    def test_update_rejects_food_field_on_medical_resource(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, resource_type=ResourceType.MEDICAL)
        headers = login_headers(client, provider.email)

        resp = client.put(
            f"/api/resources/{resource.id}",
            headers=headers,
            json={"packaging_info": "blister packs"},
        )

        assert resp.status_code == 422, resp.text

    def test_update_allergen_info_rejects_none_combined_with_others(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD)
        headers = login_headers(client, provider.email)

        resp = client.put(
            f"/api/resources/{resource.id}",
            headers=headers,
            json={"allergen_info": ["NONE", "SOY"]},
        )

        assert resp.status_code == 422, resp.text

    def test_update_preparation_time_checked_against_existing_expiry(self, client, db):
        """The resource already has expiry_time set; an update that only
        touches preparation_time must still be checked against it."""
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(
            db,
            provider,
            resource_type=ResourceType.FOOD,
            expiry_time=BASE_TIME + timedelta(hours=2),
        )
        headers = login_headers(client, provider.email)

        resp = client.put(
            f"/api/resources/{resource.id}",
            headers=headers,
            json={"preparation_time": (BASE_TIME + timedelta(hours=5)).isoformat()},
        )

        assert resp.status_code == 422, resp.text

    def test_update_other_fields_still_works_without_touching_food_fields(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(
            db, provider, resource_type=ResourceType.FOOD, food_category=None, packaging_info="loose"
        )
        headers = login_headers(client, provider.email)

        resp = client.put(f"/api/resources/{resource.id}", headers=headers, json={"quantity": 42})

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["quantity"] == 42
        # Untouched food field is preserved, not wiped by the update.
        assert data["packaging_info"] == "loose"


class TestExistingCrudUnaffectedByFoodFields:
    """Smoke tests confirming the base CRUD flow still works end-to-end
    with resources that carry no food-specific data at all."""

    def test_full_crud_cycle_without_food_fields(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        create_resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "30 loaves of bread",
                "resource_type": "FOOD",
                "quantity": 30,
                "unit": "loaves",
                "location_address": "Bakery, Bengaluru",
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        resource_id = create_resp.json()["data"]["id"]

        get_resp = client.get(f"/api/resources/{resource_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["food_category"] is None

        update_resp = client.put(f"/api/resources/{resource_id}", headers=headers, json={"quantity": 25})
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["quantity"] == 25

        delete_resp = client.delete(f"/api/resources/{resource_id}", headers=headers)
        assert delete_resp.status_code == 200

    def test_medical_resource_crud_cycle_unaffected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        create_resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "100 units paracetamol",
                "resource_type": "MEDICAL",
                "quantity": 100,
                "unit": "units",
                "location_address": "City Pharmacy, Bengaluru",
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        data = create_resp.json()["data"]
        # MEDICAL resources are still force-flagged for verification, and
        # carry no food data.
        assert data["requires_medical_verification"] is True
        assert data["food_category"] is None
