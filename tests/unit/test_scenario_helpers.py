"""Unit tests for scenario helper functions"""

from unittest.mock import MagicMock

import pytest

from web.helpers.scenario_helpers import (
    get_evaluation_overrides,
    get_scenario_summary,
    has_active_scenarios,
)
from web.models.scenario import ScenarioManager, ScenarioValue


class MockRequest:
    """Mock FastAPI Request object"""

    def __init__(self):
        self.session = {}


class MockClaim:
    """Mock Claim object"""

    def __init__(self, service: str, law: str, key: str, new_value: any, status: str = "PENDING"):
        self.service = service
        self.law = law
        self.key = key
        self.new_value = new_value
        self.status = status


class MockClaimManager:
    """Mock ClaimManagerInterface"""

    def __init__(self, claims: list[MockClaim] | None = None):
        self.claims = claims or []

    def get_claims_by_bsn(self, bsn: str, include_rejected: bool = False):
        return self.claims


class TestGetEvaluationOverrides:
    """Tests for get_evaluation_overrides function"""

    def test_no_overrides(self):
        """Test when no scenarios or claims are active"""
        request = MockRequest()
        claim_manager = MockClaimManager()

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=True,
            claim_manager=claim_manager,
            use_scenarios=False,
        )

        assert result is None

    def test_scenario_mode_with_values(self):
        """Test scenario mode with active scenario values"""
        request = MockRequest()

        # Create scenario with values
        scenario = ScenarioManager.get_or_create(request.session, "123456789", "default")
        scenario.add_value(ScenarioValue("SVC1", "law1", "key1", 100))
        scenario.add_value(ScenarioValue("SVC1", "law1", "key2", 200))
        scenario.add_value(ScenarioValue("SVC2", "law2", "key3", 300))
        ScenarioManager.save(request.session, scenario)

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="SVC1",
            law="law1",
            approved=True,
            claim_manager=None,
            use_scenarios=True,
        )

        assert result is not None
        assert "SVC1" in result
        assert result["SVC1"]["key1"] == 100
        assert result["SVC1"]["key2"] == 200
        assert "SVC2" in result
        assert result["SVC2"]["key3"] == 300

    def test_scenario_mode_empty(self):
        """Test scenario mode with no scenario values"""
        request = MockRequest()

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=True,
            claim_manager=None,
            use_scenarios=True,
        )

        assert result is None

    def test_claims_mode_with_values(self):
        """Test claims mode with pending claims"""
        request = MockRequest()
        claims = [
            MockClaim("TEST", "test_law", "key1", 100, "PENDING"),
            MockClaim("TEST", "test_law", "key2", 200, "PENDING"),
            MockClaim("OTHER", "other_law", "key3", 300, "PENDING"),  # Different service
        ]
        claim_manager = MockClaimManager(claims)

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=False,
            claim_manager=claim_manager,
            use_scenarios=False,
        )

        assert result is not None
        assert "TEST" in result
        assert result["TEST"]["key1"] == 100
        assert result["TEST"]["key2"] == 200

    def test_claims_mode_filters_service_and_law(self):
        """Test that claims are filtered by service and law"""
        request = MockRequest()
        claims = [
            MockClaim("TEST", "test_law", "key1", 100, "PENDING"),
            MockClaim("TEST", "other_law", "key2", 200, "PENDING"),  # Different law
            MockClaim("OTHER", "test_law", "key3", 300, "PENDING"),  # Different service
        ]
        claim_manager = MockClaimManager(claims)

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=False,
            claim_manager=claim_manager,
            use_scenarios=False,
        )

        assert result is not None
        assert "TEST" in result
        assert result["TEST"]["key1"] == 100
        assert "key2" not in result["TEST"]
        assert "OTHER" not in result

    def test_claims_mode_filters_status(self):
        """Test that rejected claims are filtered out"""
        request = MockRequest()
        claims = [
            MockClaim("TEST", "test_law", "key1", 100, "PENDING"),
            MockClaim("TEST", "test_law", "key2", 200, "APPROVED"),
            MockClaim("TEST", "test_law", "key3", 300, "REJECTED"),
        ]
        claim_manager = MockClaimManager(claims)

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=False,
            claim_manager=claim_manager,
            use_scenarios=False,
        )

        assert result is not None
        assert result["TEST"]["key1"] == 100
        assert result["TEST"]["key2"] == 200
        assert "key3" not in result["TEST"]

    def test_scenario_mode_ignores_claims(self):
        """Test that scenario mode uses only scenarios, ignoring claims"""
        request = MockRequest()

        # Create claims (should be ignored when use_scenarios=True)
        claims = [
            MockClaim("TEST", "test_law", "key1", 100, "PENDING"),
            MockClaim("TEST", "test_law", "key2", 200, "PENDING"),
        ]
        claim_manager = MockClaimManager(claims)

        # Create scenarios
        scenario = ScenarioManager.get_or_create(request.session, "123456789", "default")
        scenario.add_value(ScenarioValue("TEST", "test_law", "key1", 999))
        scenario.add_value(ScenarioValue("TEST", "test_law", "key3", 300))
        ScenarioManager.save(request.session, scenario)

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=False,
            claim_manager=claim_manager,
            use_scenarios=True,
        )

        assert result is not None
        # Only scenario values should be present
        assert result["TEST"]["key1"] == 999  # From scenario
        assert "key2" not in result["TEST"]  # Claim ignored in scenario mode
        assert result["TEST"]["key3"] == 300  # From scenario

    def test_no_request_in_scenario_mode(self):
        """Test scenario mode with no request returns None"""
        result = get_evaluation_overrides(
            request=None,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=True,
            claim_manager=None,
            use_scenarios=True,
        )

        assert result is None

    def test_named_scenario(self):
        """Test using a named scenario"""
        request = MockRequest()

        # Create named scenario
        scenario = ScenarioManager.get_or_create(request.session, "123456789", "test_scenario")
        scenario.add_value(ScenarioValue("TEST", "test_law", "key1", 100))
        ScenarioManager.save(request.session, scenario)

        result = get_evaluation_overrides(
            request=request,
            bsn="123456789",
            service="TEST",
            law="test_law",
            approved=True,
            claim_manager=None,
            use_scenarios=True,
            scenario_name="test_scenario",
        )

        assert result is not None
        assert result["TEST"]["key1"] == 100


class TestHasActiveScenarios:
    """Tests for has_active_scenarios function"""

    def test_with_active_scenarios(self):
        """Test when scenarios exist"""
        request = MockRequest()

        scenario = ScenarioManager.get_or_create(request.session, "123456789", "default")
        scenario.add_value(ScenarioValue("TEST", "test_law", "key", 100))
        ScenarioManager.save(request.session, scenario)

        result = has_active_scenarios(request, "123456789", "default")

        assert result is True

    def test_without_scenarios(self):
        """Test when no scenarios exist"""
        request = MockRequest()

        result = has_active_scenarios(request, "123456789", "default")

        assert result is False

    def test_no_request(self):
        """Test when request is None"""
        result = has_active_scenarios(None, "123456789", "default")

        assert result is False

    def test_named_scenario(self):
        """Test with named scenario"""
        request = MockRequest()

        scenario = ScenarioManager.get_or_create(request.session, "123456789", "test_scenario")
        scenario.add_value(ScenarioValue("TEST", "test_law", "key", 100))
        ScenarioManager.save(request.session, scenario)

        # Check named scenario exists
        assert has_active_scenarios(request, "123456789", "test_scenario") is True

        # Check default scenario doesn't exist
        assert has_active_scenarios(request, "123456789", "default") is False


class TestGetScenarioSummary:
    """Tests for get_scenario_summary function"""

    def test_with_active_scenarios(self):
        """Test summary with active scenarios"""
        request = MockRequest()

        scenario = ScenarioManager.get_or_create(request.session, "123456789", "default")
        scenario.add_value(ScenarioValue("SVC1", "law1", "key1", 100, "Label 1"))
        scenario.add_value(ScenarioValue("SVC1", "law1", "key2", 200, "Label 2"))
        scenario.add_value(ScenarioValue("SVC2", "law2", "key3", 300, "Label 3"))
        ScenarioManager.save(request.session, scenario)

        result = get_scenario_summary(request, "123456789", "default")

        assert result["active"] is True
        assert result["count"] == 3
        assert set(result["services"]) == {"SVC1", "SVC2"}
        assert len(result["values_by_service"]["SVC1"]) == 2
        assert len(result["values_by_service"]["SVC2"]) == 1
        assert "updated_at" in result

    def test_without_scenarios(self):
        """Test summary with no scenarios"""
        request = MockRequest()

        result = get_scenario_summary(request, "123456789", "default")

        assert result["active"] is False
        assert result["count"] == 0
        assert result["services"] == []

    def test_no_request(self):
        """Test summary when request is None"""
        result = get_scenario_summary(None, "123456789", "default")

        assert result["active"] is False
        assert result["count"] == 0
        assert result["services"] == []

    def test_values_grouped_by_service(self):
        """Test that values are properly grouped by service"""
        request = MockRequest()

        scenario = ScenarioManager.get_or_create(request.session, "123456789", "default")
        scenario.add_value(ScenarioValue("SVC1", "law1", "income", 30000, "Income"))
        scenario.add_value(ScenarioValue("SVC1", "law1", "age", 25, "Age"))
        scenario.add_value(ScenarioValue("SVC2", "law2", "has_children", True, "Has children"))
        ScenarioManager.save(request.session, scenario)

        result = get_scenario_summary(request, "123456789", "default")

        svc1_values = result["values_by_service"]["SVC1"]
        assert len(svc1_values) == 2
        assert any(v["key"] == "income" and v["value"] == 30000 for v in svc1_values)
        assert any(v["key"] == "age" and v["value"] == 25 for v in svc1_values)

        svc2_values = result["values_by_service"]["SVC2"]
        assert len(svc2_values) == 1
        assert svc2_values[0]["key"] == "has_children"
        assert svc2_values[0]["value"] is True
