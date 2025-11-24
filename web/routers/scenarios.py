"""
Router for managing what-if scenarios.

Scenarios allow users to temporarily override values for law calculations
without creating persistent claims. Perfect for exploring "what-if" questions.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from web.dependencies import get_case_manager, get_claim_manager, get_machine_service, templates
from web.engines import CaseManagerInterface, ClaimManagerInterface, EngineInterface
from web.models.scenario import Scenario, ScenarioManager, ScenarioValue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def parse_value(value_str: str, type_hint: str | None = None) -> Any:
    """
    Parse a string value into the appropriate Python type.

    Args:
        value_str: The string value to parse
        type_hint: Optional type hint ("boolean", "number", "date", "array", "string")

    Returns:
        Parsed value in appropriate type
    """
    if not value_str:
        return None

    # Use type hint if provided
    if type_hint:
        if type_hint == "boolean":
            return value_str.lower() in ("true", "1", "yes", "ja")
        elif type_hint == "number":
            return float(value_str) if "." in value_str else int(value_str)
        elif type_hint == "array":
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                return value_str

    # Auto-detect type
    try:
        # Try boolean
        if value_str.lower() in ("true", "false"):
            return value_str.lower() == "true"

        # Try JSON (arrays/objects)
        if value_str.startswith(("[", "{")):
            try:
                return json.loads(value_str)
            except json.JSONDecodeError:
                pass

        # Try number
        if value_str.replace(".", "", 1).replace("-", "", 1).isdigit():
            return float(value_str) if "." in value_str else int(value_str)

        # Try date
        if len(value_str.split("-")) == 3:
            from datetime import date

            try:
                year, month, day = map(int, value_str.split("-"))
                return date(year, month, day).isoformat()
            except ValueError:
                pass

    except (ValueError, AttributeError):
        pass

    # Default to string
    return value_str


@router.post("/value/set", response_class=HTMLResponse)
async def set_scenario_value(
    request: Request,
    bsn: str = Form(...),
    service: str = Form(...),
    law: str = Form(...),
    key: str = Form(...),
    value: str = Form(...),
    label: str = Form(None),
    type_hint: str = Form(None),
    scenario_name: str = Form("default"),
):
    """
    Set a scenario value in the session.

    This creates or updates a temporary override for law calculations.
    """
    try:
        # Parse the value
        parsed_value = parse_value(value, type_hint)

        # Get or create scenario
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)

        # Add the value
        scenario_value = ScenarioValue(
            service=service,
            law=law,
            key=key,
            value=parsed_value,
            label=label or key.replace("_", " ").title(),
        )
        scenario.add_value(scenario_value)

        # Save back to session
        ScenarioManager.save(request.session, scenario)

        logger.info(f"Set scenario value: {service}.{key} = {parsed_value} for BSN {bsn}")

        # Return success message with trigger to refresh law calculations
        response = templates.TemplateResponse(
            "partials/scenario_value_added.html",
            {
                "request": request,
                "key": key,
                "label": label or key,
                "value": parsed_value,
                "scenario_name": scenario_name,
            },
        )
        # Trigger law recalculation
        response.headers["HX-Trigger"] = json.dumps(
            {"scenarioChanged": {"bsn": bsn, "service": service, "law": law}, "closeDialog": True}
        )
        return response

    except Exception as e:
        logger.error(f"Error setting scenario value: {e}", exc_info=True)
        return HTMLResponse(
            f'<div class="text-red-600 p-2">Fout bij opslaan scenario: {str(e)}</div>', status_code=400
        )


@router.get("/list")
async def list_scenarios(request: Request, bsn: str):
    """Get all scenarios for a BSN"""
    try:
        scenarios = ScenarioManager.list_scenarios(request.session, bsn)

        return JSONResponse(
            {"status": "success", "scenarios": scenarios, "count": len(scenarios), "bsn": bsn}
        )
    except Exception as e:
        logger.error(f"Error listing scenarios: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/get")
async def get_scenario(request: Request, bsn: str, name: str = "default"):
    """Get a specific scenario"""
    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, name)

        return JSONResponse({"status": "success", "scenario": scenario.to_dict()})
    except Exception as e:
        logger.error(f"Error getting scenario: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/value/delete")
async def delete_scenario_value(
    request: Request, bsn: str, service: str, law: str, key: str, scenario_name: str = "default"
):
    """Delete a specific scenario value"""
    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)

        if scenario.remove_value(service, law, key):
            ScenarioManager.save(request.session, scenario)

            logger.info(f"Deleted scenario value: {service}.{key} for BSN {bsn}")

            return JSONResponse(
                {
                    "status": "success",
                    "message": f"Scenario waarde verwijderd: {key}",
                    "remaining_count": len(scenario.values),
                }
            )

        return JSONResponse({"status": "error", "message": "Scenario waarde niet gevonden"}, status_code=404)

    except Exception as e:
        logger.error(f"Error deleting scenario value: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/clear")
async def clear_scenario(request: Request, bsn: str = Form(...), scenario_name: str = Form("default")):
    """Clear all values from a scenario"""
    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)
        value_count = len(scenario.values)

        scenario.clear()
        ScenarioManager.save(request.session, scenario)

        logger.info(f"Cleared {value_count} scenario values for BSN {bsn}")

        return JSONResponse(
            {"status": "success", "message": f"{value_count} scenario waarden gewist", "cleared_count": value_count}
        )

    except Exception as e:
        logger.error(f"Error clearing scenario: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.delete("/delete")
async def delete_scenario(request: Request, bsn: str, scenario_name: str = "default"):
    """Delete an entire scenario"""
    try:
        if ScenarioManager.delete(request.session, bsn, scenario_name):
            logger.info(f"Deleted scenario '{scenario_name}' for BSN {bsn}")

            return JSONResponse({"status": "success", "message": f"Scenario '{scenario_name}' verwijderd"})

        return JSONResponse({"status": "error", "message": "Scenario niet gevonden"}, status_code=404)

    except Exception as e:
        logger.error(f"Error deleting scenario: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/clear-all")
async def clear_all_scenarios(request: Request, bsn: str = Form(...)):
    """Clear all scenarios for a BSN"""
    try:
        deleted_count = ScenarioManager.clear_all(request.session, bsn)

        logger.info(f"Cleared all scenarios for BSN {bsn} ({deleted_count} scenarios)")

        return JSONResponse(
            {"status": "success", "message": f"Alle scenario's gewist ({deleted_count})", "deleted_count": deleted_count}
        )

    except Exception as e:
        logger.error(f"Error clearing all scenarios: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/convert-to-claims")
async def convert_scenario_to_claims(
    request: Request,
    bsn: str = Form(...),
    scenario_name: str = Form("default"),
    reason: str = Form(...),
    claim_manager: ClaimManagerInterface = Depends(get_claim_manager),
):
    """
    Convert all scenario values to actual claims.

    This is useful when the user is satisfied with their scenario
    and wants to submit it as an official change request.
    """
    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)

        if not scenario.values:
            return JSONResponse(
                {"status": "error", "message": "Geen scenario waarden om te converteren"}, status_code=400
            )

        # Create claims for all scenario values
        claim_ids = []
        for scenario_value in scenario.values.values():
            claim_id = claim_manager.submit_claim(
                service=scenario_value.service,
                key=scenario_value.key,
                new_value=scenario_value.value,
                reason=f"Van scenario '{scenario_name}': {reason}",
                claimant=bsn,
                law=scenario_value.law,
                bsn=bsn,
                auto_approve=False,
            )
            claim_ids.append(claim_id)

        # Clear the scenario after conversion
        ScenarioManager.delete(request.session, bsn, scenario_name)

        logger.info(f"Converted scenario '{scenario_name}' to {len(claim_ids)} claims for BSN {bsn}")

        return JSONResponse(
            {
                "status": "success",
                "message": f"{len(claim_ids)} claims aangemaakt vanuit scenario",
                "claim_ids": claim_ids,
                "claim_count": len(claim_ids),
            }
        )

    except Exception as e:
        logger.error(f"Error converting scenario to claims: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/panel", response_class=HTMLResponse)
async def scenario_panel(request: Request, bsn: str, service: str, law: str, scenario_name: str = "default"):
    """
    Render the scenario management panel.

    This shows all active scenario values and provides controls.
    """
    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)

        # Get values for this specific service/law
        relevant_values = [v for v in scenario.values.values() if v.service == service and v.law == law]

        return templates.TemplateResponse(
            "partials/scenario_panel.html",
            {
                "request": request,
                "bsn": bsn,
                "service": service,
                "law": law,
                "scenario_name": scenario_name,
                "scenario": scenario,
                "relevant_values": relevant_values,
                "total_values": len(scenario.values),
            },
        )

    except Exception as e:
        logger.error(f"Error rendering scenario panel: {e}", exc_info=True)
        return HTMLResponse(f'<div class="text-red-600">Fout bij laden scenario panel: {str(e)}</div>')


@router.get("/form", response_class=HTMLResponse)
async def scenario_form(
    request: Request,
    bsn: str,
    service: str,
    law: str,
    key: str,
    current_value: str = None,
    label: str = None,
    type_hint: str = None,
    scenario_name: str = "default",
):
    """
    Render a form to add/edit a scenario value.

    Similar to the claim edit form, but for scenarios.
    """
    try:
        scenario = ScenarioManager.get_or_create(request.session, bsn, scenario_name)

        # Check if there's already a scenario value for this key
        existing_value = scenario.get_value(service, law, key)

        # Parse current value for display
        try:
            parsed_current = json.loads(current_value) if current_value else None
        except (json.JSONDecodeError, TypeError):
            parsed_current = current_value

        return templates.TemplateResponse(
            "partials/scenario_form.html",
            {
                "request": request,
                "bsn": bsn,
                "service": service,
                "law": law,
                "key": key,
                "label": label or key.replace("_", " ").title(),
                "current_value": parsed_current,
                "existing_value": existing_value,
                "type_hint": type_hint,
                "scenario_name": scenario_name,
            },
        )

    except Exception as e:
        logger.error(f"Error rendering scenario form: {e}", exc_info=True)
        return HTMLResponse(f'<div class="text-red-600">Fout bij laden scenario formulier: {str(e)}</div>')


@router.get("/compare", response_class=HTMLResponse)
async def compare_scenarios(
    request: Request,
    bsn: str,
    service: str,
    law: str,
    machine_service: EngineInterface = Depends(get_machine_service),
):
    """
    Compare outcomes with and without scenario values.

    Calculates the law twice:
    1. With official data (baseline)
    2. With scenario overrides (what-if)

    Shows the difference side-by-side.
    """
    try:
        from web.dependencies import TODAY

        scenario = ScenarioManager.get_or_create(request.session, bsn)

        # Calculate baseline (no scenarios)
        baseline_result = machine_service.evaluate(
            service=service,
            law=law,
            parameters={"BSN": bsn},
            reference_date=TODAY,
            approved=True,
            overwrite_input=None,
        )

        # Calculate with scenarios
        overwrite_input = scenario.get_overwrite_input() if scenario.values else None

        scenario_result = machine_service.evaluate(
            service=service,
            law=law,
            parameters={"BSN": bsn},
            reference_date=TODAY,
            approved=False,
            overwrite_input=overwrite_input,
        )

        # Calculate differences
        differences = {}
        for key, scenario_value in scenario_result.output.items():
            baseline_value = baseline_result.output.get(key)

            if baseline_value != scenario_value:
                diff = None
                if isinstance(baseline_value, (int, float)) and isinstance(scenario_value, (int, float)):
                    diff = scenario_value - baseline_value

                differences[key] = {
                    "baseline": baseline_value,
                    "scenario": scenario_value,
                    "diff": diff,
                }

        return templates.TemplateResponse(
            "partials/scenario_comparison.html",
            {
                "request": request,
                "bsn": bsn,
                "service": service,
                "law": law,
                "baseline_result": baseline_result,
                "scenario_result": scenario_result,
                "differences": differences,
                "has_differences": len(differences) > 0,
            },
        )

    except Exception as e:
        logger.error(f"Error comparing scenarios: {e}", exc_info=True)
        return HTMLResponse(f'<div class="text-red-600">Fout bij vergelijken scenarios: {str(e)}</div>')
