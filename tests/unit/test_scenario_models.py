"""Unit tests for scenario models"""

from datetime import datetime

import pytest

from web.models.scenario import Scenario, ScenarioManager, ScenarioValue


class TestScenarioValue:
    """Tests for ScenarioValue dataclass"""

    def test_create_scenario_value(self):
        """Test creating a basic scenario value"""
        value = ScenarioValue(
            service="BELASTINGDIENST",
            law="wet_inkomstenbelasting",
            key="box1_income",
            value=35000,
            label="Inkomen Box 1",
        )

        assert value.service == "BELASTINGDIENST"
        assert value.law == "wet_inkomstenbelasting"
        assert value.key == "box1_income"
        assert value.value == 35000
        assert value.label == "Inkomen Box 1"
        assert isinstance(value.timestamp, datetime)

    def test_scenario_value_without_label(self):
        """Test creating a scenario value without a label"""
        value = ScenarioValue(
            service="TEST",
            law="test_law",
            key="test_key",
            value="test_value",
        )

        assert value.label is None

    def test_scenario_value_with_different_types(self):
        """Test scenario values with different data types"""
        # Boolean value
        bool_value = ScenarioValue("SVC", "law", "flag", True)
        assert bool_value.value is True

        # Integer value
        int_value = ScenarioValue("SVC", "law", "amount", 100)
        assert int_value.value == 100

        # String value
        str_value = ScenarioValue("SVC", "law", "name", "Test Name")
        assert str_value.value == "Test Name"

        # Date value
        date_value = ScenarioValue("SVC", "law", "date", "2025-01-01")
        assert date_value.value == "2025-01-01"

    def test_scenario_value_identifier(self):
        """Test the unique identifier generation"""
        value = ScenarioValue("SVC", "law", "key", "value")
        identifier = f"{value.service}:{value.law}:{value.key}"
        assert identifier == "SVC:law:key"


class TestScenario:
    """Tests for Scenario dataclass"""

    def test_create_empty_scenario(self):
        """Test creating an empty scenario"""
        scenario = Scenario(name="default", bsn="123456789")

        assert scenario.name == "default"
        assert scenario.bsn == "123456789"
        assert len(scenario.values) == 0
        assert scenario.description == ""
        assert isinstance(scenario.created_at, datetime)
        assert isinstance(scenario.updated_at, datetime)

    def test_add_value_to_scenario(self):
        """Test adding a value to a scenario"""
        scenario = Scenario(name="default", bsn="123456789")
        value = ScenarioValue("SVC", "law", "key", 100)

        scenario.add_value(value)

        assert len(scenario.values) == 1
        assert "SVC:law:key" in scenario.values
        assert scenario.values["SVC:law:key"] == value

    def test_add_multiple_values(self):
        """Test adding multiple values to a scenario"""
        scenario = Scenario(name="default", bsn="123456789")

        value1 = ScenarioValue("SVC1", "law1", "key1", 100)
        value2 = ScenarioValue("SVC2", "law2", "key2", 200)
        value3 = ScenarioValue("SVC1", "law1", "key3", 300)

        scenario.add_value(value1)
        scenario.add_value(value2)
        scenario.add_value(value3)

        assert len(scenario.values) == 3
        assert "SVC1:law1:key1" in scenario.values
        assert "SVC2:law2:key2" in scenario.values
        assert "SVC1:law1:key3" in scenario.values

    def test_update_existing_value(self):
        """Test that adding a value with same key updates it"""
        scenario = Scenario(name="default", bsn="123456789")

        value1 = ScenarioValue("SVC", "law", "key", 100)
        scenario.add_value(value1)

        value2 = ScenarioValue("SVC", "law", "key", 200)
        scenario.add_value(value2)

        assert len(scenario.values) == 1
        assert scenario.values["SVC:law:key"].value == 200

    def test_get_value(self):
        """Test retrieving a value from a scenario"""
        scenario = Scenario(name="default", bsn="123456789")
        value = ScenarioValue("SVC", "law", "key", 100)
        scenario.add_value(value)

        retrieved = scenario.get_value("SVC", "law", "key")

        assert retrieved is not None
        assert retrieved.value == 100

    def test_get_nonexistent_value(self):
        """Test retrieving a non-existent value returns None"""
        scenario = Scenario(name="default", bsn="123456789")

        retrieved = scenario.get_value("SVC", "law", "key")

        assert retrieved is None

    def test_remove_value(self):
        """Test removing a value from a scenario"""
        scenario = Scenario(name="default", bsn="123456789")
        value = ScenarioValue("SVC", "law", "key", 100)
        scenario.add_value(value)

        scenario.remove_value("SVC", "law", "key")

        assert len(scenario.values) == 0
        assert scenario.get_value("SVC", "law", "key") is None

    def test_remove_nonexistent_value(self):
        """Test removing a non-existent value doesn't cause errors"""
        scenario = Scenario(name="default", bsn="123456789")

        # Should not raise an error
        scenario.remove_value("SVC", "law", "key")

        assert len(scenario.values) == 0

    def test_get_overwrite_input(self):
        """Test converting scenario to overwrite_input format"""
        scenario = Scenario(name="default", bsn="123456789")

        scenario.add_value(ScenarioValue("SVC1", "law1", "key1", 100))
        scenario.add_value(ScenarioValue("SVC1", "law1", "key2", 200))
        scenario.add_value(ScenarioValue("SVC2", "law2", "key3", 300))

        overwrite_input = scenario.get_overwrite_input()

        assert overwrite_input == {
            "SVC1": {"key1": 100, "key2": 200},
            "SVC2": {"key3": 300},
        }

    def test_get_overwrite_input_empty(self):
        """Test overwrite_input for empty scenario"""
        scenario = Scenario(name="default", bsn="123456789")

        overwrite_input = scenario.get_overwrite_input()

        assert overwrite_input == {}

    def test_get_values_for_service(self):
        """Test getting all values for a specific service"""
        scenario = Scenario(name="default", bsn="123456789")

        scenario.add_value(ScenarioValue("SVC1", "law1", "key1", 100))
        scenario.add_value(ScenarioValue("SVC1", "law2", "key2", 200))
        scenario.add_value(ScenarioValue("SVC2", "law3", "key3", 300))

        svc1_values = scenario.get_values_for_service("SVC1")

        assert len(svc1_values) == 2
        assert any(v.key == "key1" for v in svc1_values)
        assert any(v.key == "key2" for v in svc1_values)

    def test_to_dict(self):
        """Test converting scenario to dictionary"""
        scenario = Scenario(name="default", bsn="123456789", description="Test scenario")
        scenario.add_value(ScenarioValue("SVC", "law", "key", 100, "Test Label"))

        scenario_dict = scenario.to_dict()

        assert scenario_dict["name"] == "default"
        assert scenario_dict["bsn"] == "123456789"
        assert scenario_dict["description"] == "Test scenario"
        assert len(scenario_dict["values"]) == 1
        assert "SVC:law:key" in scenario_dict["values"]
        assert scenario_dict["values"]["SVC:law:key"]["value"] == 100

    def test_from_dict(self):
        """Test creating scenario from dictionary"""
        scenario_dict = {
            "name": "default",
            "bsn": "123456789",
            "description": "Test scenario",
            "created_at": "2025-01-24T10:00:00",
            "updated_at": "2025-01-24T10:00:00",
            "values": {
                "SVC:law:key": {
                    "service": "SVC",
                    "law": "law",
                    "key": "key",
                    "value": 100,
                    "label": "Test Label",
                    "timestamp": "2025-01-24T10:00:00",
                }
            },
        }

        scenario = Scenario.from_dict(scenario_dict)

        assert scenario.name == "default"
        assert scenario.bsn == "123456789"
        assert scenario.description == "Test scenario"
        assert len(scenario.values) == 1
        assert scenario.get_value("SVC", "law", "key").value == 100


class TestScenarioManager:
    """Tests for ScenarioManager"""

    def test_get_or_create_new_scenario(self):
        """Test creating a new scenario when none exists"""
        session = {}

        scenario = ScenarioManager.get_or_create(session, "123456789", "default")

        assert scenario.name == "default"
        assert scenario.bsn == "123456789"
        assert len(scenario.values) == 0

    def test_get_existing_scenario(self):
        """Test retrieving an existing scenario"""
        session = {}

        # Create and save a scenario
        scenario1 = ScenarioManager.get_or_create(session, "123456789", "default")
        scenario1.add_value(ScenarioValue("SVC", "law", "key", 100))
        ScenarioManager.save(session, scenario1)

        # Retrieve it again
        scenario2 = ScenarioManager.get_or_create(session, "123456789", "default")

        assert len(scenario2.values) == 1
        assert scenario2.get_value("SVC", "law", "key").value == 100

    def test_save_scenario(self):
        """Test saving a scenario to session"""
        session = {}

        scenario = Scenario(name="default", bsn="123456789")
        scenario.add_value(ScenarioValue("SVC", "law", "key", 100))

        ScenarioManager.save(session, scenario)

        session_key = "scenarios:123456789:default"
        assert session_key in session
        assert session[session_key]["values"]["SVC:law:key"]["value"] == 100

    def test_delete_scenario(self):
        """Test deleting a scenario from session"""
        session = {}

        # Create and save a scenario
        scenario = ScenarioManager.get_or_create(session, "123456789", "default")
        ScenarioManager.save(session, scenario)

        # Delete it
        ScenarioManager.delete(session, "123456789", "default")

        session_key = "scenarios:123456789:default"
        assert session_key not in session

    def test_list_scenarios_empty(self):
        """Test listing scenarios when none exist"""
        session = {}

        scenarios = ScenarioManager.list_scenarios(session, "123456789")

        assert scenarios == []

    def test_list_scenarios(self):
        """Test listing multiple scenarios"""
        session = {}

        # Create multiple scenarios
        scenario1 = ScenarioManager.get_or_create(session, "123456789", "default")
        ScenarioManager.save(session, scenario1)

        scenario2 = ScenarioManager.get_or_create(session, "123456789", "test")
        ScenarioManager.save(session, scenario2)

        # Create scenario for different BSN (should not be listed)
        scenario3 = ScenarioManager.get_or_create(session, "987654321", "default")
        ScenarioManager.save(session, scenario3)

        scenarios = ScenarioManager.list_scenarios(session, "123456789")

        assert len(scenarios) == 2
        # list_scenarios returns dicts, not Scenario objects
        scenario_names = [s["name"] for s in scenarios]
        assert "default" in scenario_names
        assert "test" in scenario_names

    def test_clear_all_scenarios(self):
        """Test clearing all scenarios for a BSN"""
        session = {}

        # Create multiple scenarios
        scenario1 = ScenarioManager.get_or_create(session, "123456789", "default")
        scenario1.add_value(ScenarioValue("SVC", "law", "key", 100))
        ScenarioManager.save(session, scenario1)

        scenario2 = ScenarioManager.get_or_create(session, "123456789", "test")
        scenario2.add_value(ScenarioValue("SVC", "law", "key", 200))
        ScenarioManager.save(session, scenario2)

        # Create scenario for different BSN (should not be cleared)
        scenario3 = ScenarioManager.get_or_create(session, "987654321", "default")
        ScenarioManager.save(session, scenario3)

        # Clear all for first BSN
        ScenarioManager.clear_all(session, "123456789")

        # Check first BSN scenarios are gone
        scenarios = ScenarioManager.list_scenarios(session, "123456789")
        assert len(scenarios) == 0

        # Check second BSN scenario still exists
        scenarios2 = ScenarioManager.list_scenarios(session, "987654321")
        assert len(scenarios2) == 1

    def test_multiple_bsns_isolation(self):
        """Test that scenarios for different BSNs are isolated"""
        session = {}

        # Create scenarios for different BSNs
        scenario1 = ScenarioManager.get_or_create(session, "123456789", "default")
        scenario1.add_value(ScenarioValue("SVC", "law", "key", 100))
        ScenarioManager.save(session, scenario1)

        scenario2 = ScenarioManager.get_or_create(session, "987654321", "default")
        scenario2.add_value(ScenarioValue("SVC", "law", "key", 200))
        ScenarioManager.save(session, scenario2)

        # Retrieve and verify isolation
        retrieved1 = ScenarioManager.get_or_create(session, "123456789", "default")
        retrieved2 = ScenarioManager.get_or_create(session, "987654321", "default")

        assert retrieved1.get_value("SVC", "law", "key").value == 100
        assert retrieved2.get_value("SVC", "law", "key").value == 200
