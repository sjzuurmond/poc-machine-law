"""Integration tests for scenario API endpoints"""

import json

import pytest
from fastapi.testclient import TestClient

from web.main import app
from web.models.scenario import ScenarioManager, ScenarioValue

client = TestClient(app)


class TestScenarioValueSet:
    """Tests for POST /scenarios/value/set endpoint"""

    def test_set_scenario_value(self):
        """Test setting a scenario value"""
        response = client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "BELASTINGDIENST",
                "law": "wet_inkomstenbelasting",
                "key": "box1_income",
                "value": "35000",
                "label": "Inkomen Box 1",
                "type_hint": "number",
            },
        )

        assert response.status_code == 200
        assert "HX-Trigger" in response.headers

    def test_set_boolean_value(self):
        """Test setting a boolean scenario value"""
        response = client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "has_partner",
                "value": "true",
                "type_hint": "boolean",
            },
        )

        assert response.status_code == 200

    def test_set_value_without_label(self):
        """Test setting a value without a label"""
        response = client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "value": "test_value",
            },
        )

        assert response.status_code == 200


class TestScenarioList:
    """Tests for GET /scenarios/list endpoint"""

    def test_list_empty_scenarios(self):
        """Test listing scenarios when none exist"""
        response = client.get("/scenarios/list", params={"bsn": "123456789"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 0
        assert data["scenarios"] == []

    def test_list_scenarios_after_setting_value(self):
        """Test listing scenarios after setting a value"""
        # Set a value first
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "value": "100",
            },
        )

        # List scenarios
        response = client.get("/scenarios/list", params={"bsn": "123456789"})

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["count"] == 1
        assert len(data["scenarios"]) == 1
        assert data["scenarios"][0]["name"] == "default"


class TestScenarioGet:
    """Tests for GET /scenarios/get endpoint"""

    def test_get_nonexistent_scenario(self):
        """Test getting a scenario that doesn't exist"""
        response = client.get(
            "/scenarios/get",
            params={"bsn": "123456789", "scenario_name": "nonexistent"},
        )

        assert response.status_code == 404

    def test_get_existing_scenario(self):
        """Test getting an existing scenario"""
        # Create a scenario first
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "value": "100",
            },
        )

        # Get the scenario
        response = client.get(
            "/scenarios/get",
            params={"bsn": "123456789", "scenario_name": "default"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["scenario"]["name"] == "default"
        assert data["scenario"]["bsn"] == "123456789"
        assert len(data["scenario"]["values"]) == 1


class TestScenarioValueDelete:
    """Tests for DELETE /scenarios/value/delete endpoint"""

    def test_delete_scenario_value(self):
        """Test deleting a specific scenario value"""
        # Create a scenario with a value
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "value": "100",
            },
        )

        # Delete the value
        response = client.delete(
            "/scenarios/value/delete",
            params={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "scenario_name": "default",
            },
        )

        assert response.status_code == 200

        # Verify it's deleted
        get_response = client.get(
            "/scenarios/get",
            params={"bsn": "123456789", "scenario_name": "default"},
        )
        data = get_response.json()
        assert len(data["scenario"]["values"]) == 0

    def test_delete_nonexistent_value(self):
        """Test deleting a value that doesn't exist"""
        response = client.delete(
            "/scenarios/value/delete",
            params={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "nonexistent",
                "scenario_name": "default",
            },
        )

        # Should still succeed (idempotent)
        assert response.status_code == 200


class TestScenarioClear:
    """Tests for POST /scenarios/clear endpoint"""

    def test_clear_scenario(self):
        """Test clearing all values from a scenario"""
        # Create scenario with multiple values
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "key1",
                "value": "100",
            },
        )
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "key2",
                "value": "200",
            },
        )

        # Clear the scenario
        response = client.post(
            "/scenarios/clear",
            data={"bsn": "123456789", "scenario_name": "default"},
        )

        assert response.status_code == 200

        # Verify it's cleared
        get_response = client.get(
            "/scenarios/get",
            params={"bsn": "123456789", "scenario_name": "default"},
        )
        data = get_response.json()
        assert len(data["scenario"]["values"]) == 0

    def test_clear_nonexistent_scenario(self):
        """Test clearing a scenario that doesn't exist"""
        response = client.post(
            "/scenarios/clear",
            data={"bsn": "123456789", "scenario_name": "nonexistent"},
        )

        # Should still succeed (idempotent)
        assert response.status_code == 200


class TestScenarioForm:
    """Tests for GET /scenarios/form endpoint"""

    def test_get_scenario_form(self):
        """Test getting the scenario form"""
        response = client.get(
            "/scenarios/form",
            params={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "current_value": "100",
                "label": "Test Label",
            },
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Test Label" in response.content

    def test_get_form_with_boolean_type(self):
        """Test getting form with boolean type hint"""
        response = client.get(
            "/scenarios/form",
            params={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "has_partner",
                "current_value": "false",
                "type_hint": "boolean",
            },
        )

        assert response.status_code == 200
        assert b"radio" in response.content or b"checkbox" in response.content

    def test_get_form_with_number_type(self):
        """Test getting form with number type hint"""
        response = client.get(
            "/scenarios/form",
            params={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "income",
                "current_value": "30000",
                "type_hint": "number",
            },
        )

        assert response.status_code == 200
        assert b"number" in response.content or b"30000" in response.content


class TestScenarioCompare:
    """Tests for GET /scenarios/compare endpoint"""

    def test_compare_without_scenarios(self):
        """Test comparison when no scenarios exist"""
        response = client.get(
            "/scenarios/compare",
            params={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
            },
        )

        # Should return HTML indicating no scenarios
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_compare_with_scenarios(self):
        """Test comparison with active scenarios"""
        # Create a scenario
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "value": "200",
            },
        )

        response = client.get(
            "/scenarios/compare",
            params={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
            },
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestValueParsing:
    """Tests for value parsing with different type hints"""

    def test_parse_boolean_true(self):
        """Test parsing boolean true values"""
        for value in ["true", "True", "TRUE", "yes", "1"]:
            response = client.post(
                "/scenarios/value/set",
                data={
                    "bsn": "123456789",
                    "service": "TEST",
                    "law": "test_law",
                    "key": "test_bool",
                    "value": value,
                    "type_hint": "boolean",
                },
            )
            assert response.status_code == 200

    def test_parse_boolean_false(self):
        """Test parsing boolean false values"""
        for value in ["false", "False", "FALSE", "no", "0"]:
            response = client.post(
                "/scenarios/value/set",
                data={
                    "bsn": "123456789",
                    "service": "TEST",
                    "law": "test_law",
                    "key": "test_bool",
                    "value": value,
                    "type_hint": "boolean",
                },
            )
            assert response.status_code == 200

    def test_parse_number_integer(self):
        """Test parsing integer values"""
        response = client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_number",
                "value": "12345",
                "type_hint": "number",
            },
        )
        assert response.status_code == 200

    def test_parse_number_float(self):
        """Test parsing float values"""
        response = client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_number",
                "value": "123.45",
                "type_hint": "number",
            },
        )
        assert response.status_code == 200

    def test_parse_date(self):
        """Test parsing date values"""
        response = client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_date",
                "value": "2025-01-24",
                "type_hint": "date",
            },
        )
        assert response.status_code == 200


class TestMultipleScenarios:
    """Tests for working with multiple scenarios"""

    def test_multiple_named_scenarios(self):
        """Test creating multiple named scenarios"""
        # Create scenario 1
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "key1",
                "value": "100",
                "scenario_name": "scenario1",
            },
        )

        # Create scenario 2
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "key2",
                "value": "200",
                "scenario_name": "scenario2",
            },
        )

        # List scenarios
        response = client.get("/scenarios/list", params={"bsn": "123456789"})

        data = response.json()
        assert data["count"] == 2
        scenario_names = [s["name"] for s in data["scenarios"]]
        assert "scenario1" in scenario_names
        assert "scenario2" in scenario_names

    def test_scenarios_isolated_by_bsn(self):
        """Test that scenarios for different BSNs are isolated"""
        # Create scenario for BSN 1
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "123456789",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "value": "100",
            },
        )

        # Create scenario for BSN 2
        client.post(
            "/scenarios/value/set",
            data={
                "bsn": "987654321",
                "service": "TEST",
                "law": "test_law",
                "key": "test_key",
                "value": "200",
            },
        )

        # List scenarios for BSN 1
        response1 = client.get("/scenarios/list", params={"bsn": "123456789"})
        data1 = response1.json()

        # List scenarios for BSN 2
        response2 = client.get("/scenarios/list", params={"bsn": "987654321"})
        data2 = response2.json()

        # Both should have 1 scenario
        assert data1["count"] == 1
        assert data2["count"] == 1
