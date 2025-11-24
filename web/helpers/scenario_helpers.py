"""
Helper functions for integrating scenarios into law evaluation.

These functions provide clean integration between the scenario system
and the existing law evaluation engine.
"""

import logging
from typing import Any

from fastapi import Request

from web.engines import ClaimManagerInterface
from web.models.scenario import ScenarioManager

logger = logging.getLogger(__name__)


def get_evaluation_overrides(
    request: Request | None,
    bsn: str,
    service: str,
    law: str,
    approved: bool,
    claim_manager: ClaimManagerInterface | None,
    use_scenarios: bool = False,
    scenario_name: str = "default",
) -> dict[str, dict[str, Any]] | None:
    """
    Build overwrite_input for law evaluation based on mode.

    Supports three modes:
    1. Claims mode (approved=False, use_scenarios=False): Use pending claims
    2. Scenario mode (use_scenarios=True): Use session scenarios
    3. Mixed mode: Scenarios override claims

    Args:
        request: FastAPI request (needed for session access)
        bsn: BSN of the person
        service: Service name
        law: Law name
        approved: Whether to include only approved claims
        claim_manager: Claim manager instance
        use_scenarios: Whether to use scenarios
        scenario_name: Name of scenario to use

    Returns:
        Dictionary of overrides {service: {key: value}} or None if no overrides
    """
    overwrite_input = None

    # Mode 1: Get claims
    if not use_scenarios and claim_manager:
        overwrite_input = _get_claim_overrides(claim_manager, bsn, service, law, approved)

    # Mode 2: Get scenarios (can merge with claims if both are enabled)
    if use_scenarios and request:
        scenario_overrides = _get_scenario_overrides(request, bsn, scenario_name)

        if scenario_overrides:
            if overwrite_input is None:
                overwrite_input = scenario_overrides
            else:
                # Merge scenarios with claims, scenarios take precedence
                for svc, values in scenario_overrides.items():
                    if svc not in overwrite_input:
                        overwrite_input[svc] = {}
                    overwrite_input[svc].update(values)

    return overwrite_input


def _get_claim_overrides(
    claim_manager: ClaimManagerInterface, bsn: str, service: str, law: str, approved: bool
) -> dict[str, dict[str, Any]] | None:
    """Get overrides from claims"""
    try:
        claims = claim_manager.get_claims_by_bsn(bsn, include_rejected=False)

        # Filter claims for this service and law
        relevant_claims = [
            claim
            for claim in claims
            if claim.service == service and claim.law == law and claim.status in ["PENDING", "APPROVED"]
        ]

        if not relevant_claims:
            return None

        # Build overwrite dictionary
        overwrite_input = {}
        for claim in relevant_claims:
            # Claims are already structured by service/key
            if service not in overwrite_input:
                overwrite_input[service] = {}
            overwrite_input[service][claim.key] = claim.new_value

        logger.debug(f"Using {len(relevant_claims)} claims as overrides for {service}.{law}")
        return overwrite_input

    except Exception as e:
        logger.error(f"Error getting claim overrides: {e}", exc_info=True)
        return None


def _get_scenario_overrides(request: Request, bsn: str, scenario_name: str) -> dict[str, dict[str, Any]] | None:
    """Get overrides from session scenarios"""
    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)

        if not scenario.values:
            return None

        overwrite_input = scenario.get_overwrite_input()

        logger.debug(f"Using {len(scenario.values)} scenario values as overrides")
        return overwrite_input

    except Exception as e:
        logger.error(f"Error getting scenario overrides: {e}", exc_info=True)
        return None


def has_active_scenarios(request: Request | None, bsn: str, scenario_name: str = "default") -> bool:
    """
    Check if there are active scenarios for a BSN.

    Useful for UI to show scenario mode indicator.
    """
    if not request:
        return False

    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)
        return len(scenario.values) > 0
    except Exception:
        return False


def get_scenario_summary(request: Request | None, bsn: str, scenario_name: str = "default") -> dict[str, Any]:
    """
    Get a summary of active scenarios.

    Returns information about what values are overridden.
    """
    if not request:
        return {"active": False, "count": 0, "services": []}

    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)

        if not scenario.values:
            return {"active": False, "count": 0, "services": []}

        # Group by service
        services = {}
        for value in scenario.values.values():
            if value.service not in services:
                services[value.service] = []
            services[value.service].append({"key": value.key, "label": value.label, "value": value.value})

        return {
            "active": True,
            "count": len(scenario.values),
            "services": list(services.keys()),
            "values_by_service": services,
            "updated_at": scenario.updated_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting scenario summary: {e}", exc_info=True)
        return {"active": False, "count": 0, "services": [], "error": str(e)}
