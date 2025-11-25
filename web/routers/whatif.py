"""Whatif scenarios router for exploring government benefits changes"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from web.dependencies import TODAY, get_machine_service, templates
from web.engines import EngineInterface

router = APIRouter(prefix="/whatif", tags=["whatif"])

logger = logging.getLogger(__name__)


# Scenario template definitions
SCENARIO_TEMPLATES = {
    "income_increase": {
        "title": "Mijn inkomen verandert",
        "description": "Ik ga meer uren werken of krijg loonsverhoging",
        "keywords": ["inkomen", "vermogen", "loon", "salaris"],
        "icon": "💰",
    },
    "moving": {
        "title": "Ik ga verhuizen",
        "description": "Ik verhuis naar andere woning",
        "keywords": ["huur", "postcode", "woonplaats", "adres"],
        "icon": "🏠",
    },
    "relationship_change": {
        "title": "Ik ga samenwonen/scheiden",
        "description": "Mijn relatiestatus verandert",
        "keywords": ["burgerlijk", "partner", "gehuwd", "samenwonen"],
        "icon": "👥",
    },
    "self_employed": {
        "title": "Ik word zelfstandig ondernemer",
        "description": "Ik start als ZZP'er of ondernemer",
        "keywords": ["inkomen", "onderneming", "zelfstandig", "zzp"],
        "icon": "💼",
    },
    "retirement": {
        "title": "Ik ga met pensioen",
        "description": "Ik stop met werken en ontvang pensioen",
        "keywords": ["aow", "pensioen", "inkomen", "uitkering"],
        "icon": "👴",
    },
    "custom": {
        "title": "Aangepast scenario",
        "description": "Maak je eigen scenario met alle velden",
        "keywords": None,  # Show all fields
        "icon": "⚙️",
    },
}


def get_fields_from_law_inputs(
    bsn: str,
    laws: list[dict[str, str]],
    machine_service: EngineInterface,
    focus_keywords: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Extract fields from law inputs that can be modified in whatif scenarios.

    Args:
        bsn: Citizen identifier
        laws: List of discoverable laws [{"service": ..., "law": ...}, ...]
        machine_service: Engine interface for law evaluation
        focus_keywords: Keywords to filter fields (e.g., ["inkomen", "huur"])

    Returns:
        Dictionary of {field_key: {"value": ..., "label": ..., "type": ...}}
    """
    fields = {}

    for law_info in laws:
        service = law_info["service"]
        law = law_info["law"]

        try:
            # Evaluate the law to get current input values
            result = machine_service.evaluate(
                service=service,
                law=law,
                parameters={"BSN": bsn},
                reference_date=TODAY,
                effective_date=None,
                approved=False,
            )

            # Get rule spec to understand field types
            rule_spec = machine_service.get_rule_spec(law, TODAY, service)
            input_properties = rule_spec.get("properties", {}).get("input", [])

            # Create a map of property names to their specs
            property_map = {prop.get("name"): prop for prop in input_properties if prop.get("name")}

            # Extract fields from result.input
            for field_key, field_value in result.input.items():
                # Skip BSN and computed fields
                if field_key.upper() in ["BSN", "LEEFTIJD", "AGE"]:
                    continue

                # Get property spec for this field
                prop_spec = property_map.get(field_key)

                # Filter by keywords if specified
                if focus_keywords:
                    field_key_lower = field_key.lower()
                    if not any(keyword.lower() in field_key_lower for keyword in focus_keywords):
                        continue

                # Determine field type
                field_type = "text"
                if prop_spec:
                    prop_type = prop_spec.get("type")
                    if prop_type in ["number", "integer"]:
                        field_type = "number"
                    elif prop_type == "boolean":
                        field_type = "boolean"
                    elif prop_type == "date":
                        field_type = "date"

                # Create label from field key
                label = field_key.replace("_", " ").title()

                # Store field info
                field_full_key = f"{service}.{law}.{field_key}"
                if field_full_key not in fields:  # Avoid duplicates
                    fields[field_full_key] = {
                        "key": field_key,
                        "service": service,
                        "law": law,
                        "value": field_value,
                        "label": label,
                        "type": field_type,
                        "spec": prop_spec,
                    }

        except Exception as e:
            logger.warning(f"Could not extract fields from {service}/{law}: {e}")
            continue

    return fields


def create_slider_configs(fields: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Create slider configurations for numeric fields with intelligent min/max/step.

    Args:
        fields: Dictionary of fields from get_fields_from_law_inputs

    Returns:
        Dictionary with slider configurations added to numeric fields
    """
    slider_fields = {}

    for field_key, field_info in fields.items():
        if field_info["type"] != "number":
            continue

        current_value = field_info["value"]
        if current_value is None:
            current_value = 0

        # Convert cents to euros if it looks like a currency field (>1000)
        is_currency = current_value > 1000 or "inkomen" in field_key.lower() or "bedrag" in field_key.lower()

        # Determine intelligent min/max/step based on field name
        field_key_lower = field_key.lower()

        if "inkomen" in field_key_lower or "loon" in field_key_lower or "salaris" in field_key_lower:
            # Income fields
            min_val = 0
            max_val = max(10000000, current_value * 2)  # €100k or 2x current (in cents)
            step = 100000  # €1000 steps
        elif "huur" in field_key_lower or "woonlasten" in field_key_lower:
            # Rent fields
            min_val = 0
            max_val = 250000  # €2500 in cents
            step = 5000  # €50 steps
        elif "vermogen" in field_key_lower or "spaargeld" in field_key_lower:
            # Wealth fields
            min_val = 0
            max_val = max(30000000, current_value * 2)  # €300k or 2x current
            step = 500000  # €5000 steps
        else:
            # Generic numeric field
            min_val = 0
            max_val = max(current_value * 2, 1000000)
            step = max(1, current_value // 100)  # 1% of current value

        slider_fields[field_key] = {
            **field_info,
            "slider": {
                "min": min_val,
                "max": max_val,
                "step": step,
                "current": current_value,
                "is_currency": is_currency,
            },
        }

    return slider_fields


def calculate_law_with_overwrite(
    bsn: str, service: str, law: str, overwrite_input: dict[str, Any], machine_service: EngineInterface
) -> dict[str, Any]:
    """
    Calculate a law with modified input values.

    Returns:
        Dictionary with result info including output, input, and requirements_met
    """
    try:
        result = machine_service.evaluate(
            service=service,
            law=law,
            parameters={"BSN": bsn},
            reference_date=TODAY,
            effective_date=None,
            approved=False,
            overwrite_input=overwrite_input,
        )

        return {
            "service": service,
            "law": law,
            "output": result.output,
            "input": result.input,
            "requirements_met": result.requirements_met,
            "missing_required": result.missing_required,
            "success": True,
        }
    except Exception as e:
        logger.error(f"Error calculating {service}/{law}: {e}")
        return {
            "service": service,
            "law": law,
            "success": False,
            "error": str(e),
        }


def get_primary_output_field(law: str, output: dict[str, Any], machine_service: EngineInterface) -> dict[str, Any]:
    """
    Get the primary citizen-relevant output field from a law result.

    Returns:
        Dictionary with {"key": ..., "value": ..., "label": ...}
    """
    # Common primary field patterns
    primary_patterns = [
        "hoogte_toeslag",
        "subsidiebedrag",
        "uitkeringsbedrag",
        "pensioenbedrag",
        "totale_belastingschuld",
        "bedrag",
        "toeslag",
    ]

    for pattern in primary_patterns:
        for key in output:
            if pattern in key.lower():
                return {
                    "key": key,
                    "value": output[key],
                    "label": key.replace("_", " ").title(),
                }

    # Fallback: return first numeric value
    for key, value in output.items():
        if isinstance(value, (int, float)) and value != 0:
            return {
                "key": key,
                "value": value,
                "label": key.replace("_", " ").title(),
            }

    # Last resort: return first field
    if output:
        key = list(output.keys())[0]
        return {
            "key": key,
            "value": output[key],
            "label": key.replace("_", " ").title(),
        }

    return {"key": "result", "value": None, "label": "Result"}


@router.get("/")
async def whatif_index(request: Request, bsn: str = "100000001"):
    """Main whatif scenarios page with navigation to different patterns"""
    return templates.TemplateResponse(
        "whatif/index.html",
        {
            "request": request,
            "bsn": bsn,
        },
    )


@router.get("/direct-manipulation")
async def direct_manipulation(
    request: Request, bsn: str = "100000001", machine_service: EngineInterface = Depends(get_machine_service)
):
    """Pattern 1: Direct manipulation with real-time sliders"""

    # Get discoverable laws
    discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)

    # Extract all numeric fields
    all_fields = get_fields_from_law_inputs(bsn, discoverable_laws, machine_service, focus_keywords=None)

    # Create slider configs for numeric fields only
    slider_fields = create_slider_configs(all_fields)

    # Calculate baseline results for each law
    baseline_results = {}
    for law_info in discoverable_laws:
        service = law_info["service"]
        law = law_info["law"]

        result_info = calculate_law_with_overwrite(bsn, service, law, {}, machine_service)
        if result_info["success"]:
            baseline_results[f"{service}.{law}"] = result_info

    return templates.TemplateResponse(
        "whatif/direct_manipulation.html",
        {
            "request": request,
            "bsn": bsn,
            "slider_fields": slider_fields,
            "baseline_results": baseline_results,
            "discoverable_laws": discoverable_laws,
        },
    )


@router.post("/calculate-direct")
async def calculate_direct(
    request: Request,
    bsn: str = Form(...),
    machine_service: EngineInterface = Depends(get_machine_service),
):
    """Calculate law results with modified values from direct manipulation"""

    # Get form data
    form_data = await request.form()

    # Build overwrite_input from form data
    overwrite_by_law: dict[str, dict[str, Any]] = {}

    for key, value in form_data.items():
        if key == "bsn":
            continue

        # Parse key format: service.law.field
        parts = key.split(".")
        if len(parts) != 3:
            continue

        service, law, field = parts
        law_key = f"{service}.{law}"

        if law_key not in overwrite_by_law:
            overwrite_by_law[law_key] = {}

        # Convert value to appropriate type
        try:
            # Try to convert to number (cents)
            overwrite_by_law[law_key][field] = int(value)
        except ValueError:
            overwrite_by_law[law_key][field] = value

    # Calculate new results for each law
    new_results = {}
    discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)

    for law_info in discoverable_laws:
        service = law_info["service"]
        law = law_info["law"]
        law_key = f"{service}.{law}"

        overwrite_input = overwrite_by_law.get(law_key, {})
        result_info = calculate_law_with_overwrite(bsn, service, law, overwrite_input, machine_service)

        if result_info["success"]:
            new_results[law_key] = result_info

    return templates.TemplateResponse(
        "whatif/partials/direct_results.html",
        {
            "request": request,
            "bsn": bsn,
            "results": new_results,
        },
    )


@router.get("/templates")
async def template_scenarios(request: Request, bsn: str = "100000001"):
    """Pattern 2: Template scenarios for common life situations"""

    return templates.TemplateResponse(
        "whatif/templates.html",
        {
            "request": request,
            "bsn": bsn,
            "scenarios": SCENARIO_TEMPLATES,
        },
    )


@router.get("/templates/{scenario_id}")
async def template_scenario_form(
    request: Request,
    scenario_id: str,
    bsn: str = "100000001",
    machine_service: EngineInterface = Depends(get_machine_service),
):
    """Show form for a specific template scenario"""

    scenario = SCENARIO_TEMPLATES.get(scenario_id)
    if not scenario:
        return HTMLResponse("Scenario not found", status_code=404)

    # Get discoverable laws
    discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)

    # Extract fields filtered by scenario keywords
    keywords = scenario.get("keywords")
    fields = get_fields_from_law_inputs(bsn, discoverable_laws, machine_service, focus_keywords=keywords)

    return templates.TemplateResponse(
        "whatif/partials/scenario_form.html",
        {
            "request": request,
            "bsn": bsn,
            "scenario_id": scenario_id,
            "scenario": scenario,
            "fields": fields,
        },
    )


@router.post("/templates/calculate")
async def calculate_template(
    request: Request,
    bsn: str = Form(...),
    scenario_id: str = Form(...),
    machine_service: EngineInterface = Depends(get_machine_service),
):
    """Calculate results for a template scenario"""

    # Get form data
    form_data = await request.form()

    # Build overwrite_input from form data
    overwrite_by_law: dict[str, dict[str, Any]] = {}

    for key, value in form_data.items():
        if key in ["bsn", "scenario_id"]:
            continue

        # Parse key format: service.law.field
        parts = key.split(".")
        if len(parts) != 3:
            continue

        service, law, field = parts
        law_key = f"{service}.{law}"

        if law_key not in overwrite_by_law:
            overwrite_by_law[law_key] = {}

        # Convert value to appropriate type
        try:
            overwrite_by_law[law_key][field] = int(value)
        except ValueError:
            overwrite_by_law[law_key][field] = value

    # Calculate baseline and new results
    discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)

    comparisons = []
    for law_info in discoverable_laws:
        service = law_info["service"]
        law = law_info["law"]
        law_key = f"{service}.{law}"

        # Baseline
        baseline = calculate_law_with_overwrite(bsn, service, law, {}, machine_service)

        # Modified
        overwrite_input = overwrite_by_law.get(law_key, {})
        if overwrite_input:  # Only calculate if there are changes for this law
            modified = calculate_law_with_overwrite(bsn, service, law, overwrite_input, machine_service)

            if baseline["success"] and modified["success"]:
                # Get primary output fields
                baseline_output = get_primary_output_field(law, baseline["output"], machine_service)
                modified_output = get_primary_output_field(law, modified["output"], machine_service)

                # Calculate delta
                baseline_value = baseline_output.get("value", 0) or 0
                modified_value = modified_output.get("value", 0) or 0
                delta = modified_value - baseline_value

                comparisons.append(
                    {
                        "service": service,
                        "law": law,
                        "law_name": law.split("/")[-1].replace("_", " ").title(),
                        "baseline_value": baseline_value,
                        "modified_value": modified_value,
                        "delta": delta,
                        "field_label": baseline_output.get("label", "Result"),
                    }
                )

    scenario = SCENARIO_TEMPLATES.get(scenario_id, {})

    return templates.TemplateResponse(
        "whatif/partials/scenario_results.html",
        {
            "request": request,
            "bsn": bsn,
            "scenario": scenario,
            "comparisons": comparisons,
        },
    )


@router.get("/comparison")
async def comparison_mode(
    request: Request, bsn: str = "100000001", machine_service: EngineInterface = Depends(get_machine_service)
):
    """Pattern 3: Side-by-side comparison of multiple scenarios"""

    # Get discoverable laws
    discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)

    # Extract all fields
    all_fields = get_fields_from_law_inputs(bsn, discoverable_laws, machine_service, focus_keywords=None)

    # Calculate baseline results
    baseline_results = {}
    for law_info in discoverable_laws:
        service = law_info["service"]
        law = law_info["law"]

        result_info = calculate_law_with_overwrite(bsn, service, law, {}, machine_service)
        if result_info["success"]:
            baseline_results[f"{service}.{law}"] = result_info

    return templates.TemplateResponse(
        "whatif/comparison.html",
        {
            "request": request,
            "bsn": bsn,
            "fields": all_fields,
            "baseline_results": baseline_results,
            "discoverable_laws": discoverable_laws,
        },
    )


@router.post("/comparison/calculate")
async def calculate_comparison(
    request: Request,
    bsn: str = Form(...),
    machine_service: EngineInterface = Depends(get_machine_service),
):
    """Calculate results for comparison scenarios"""

    # Get form data
    form_data = await request.form()

    # Parse scenarios from form data
    # Format: scenario_{idx}_{service}.{law}.{field}
    scenarios_data: dict[int, dict[str, dict[str, Any]]] = {}

    for key, value in form_data.items():
        if key == "bsn":
            continue

        # Parse scenario index and field
        if not key.startswith("scenario_"):
            continue

        parts = key.split("_", 2)  # Split into ['scenario', idx, rest]
        if len(parts) < 3:
            continue

        scenario_idx = int(parts[1])
        field_path = parts[2]

        # Parse field path: service.law.field or name
        if field_path == "name":
            # Scenario name
            if scenario_idx not in scenarios_data:
                scenarios_data[scenario_idx] = {"name": value, "overwrites": {}}
            else:
                scenarios_data[scenario_idx]["name"] = value
            continue

        field_parts = field_path.split(".")
        if len(field_parts) != 3:
            continue

        service, law, field = field_parts
        law_key = f"{service}.{law}"

        # Initialize scenario data
        if scenario_idx not in scenarios_data:
            scenarios_data[scenario_idx] = {"name": f"Scenario {scenario_idx}", "overwrites": {}}

        if law_key not in scenarios_data[scenario_idx]["overwrites"]:
            scenarios_data[scenario_idx]["overwrites"][law_key] = {}

        # Convert value to appropriate type
        try:
            scenarios_data[scenario_idx]["overwrites"][law_key][field] = int(value)
        except ValueError:
            scenarios_data[scenario_idx]["overwrites"][law_key][field] = value

    # Calculate results for each scenario
    discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)

    # Baseline calculation
    baseline_results = {}
    for law_info in discoverable_laws:
        service = law_info["service"]
        law = law_info["law"]
        law_key = f"{service}.{law}"

        result = calculate_law_with_overwrite(bsn, service, law, {}, machine_service)
        if result["success"]:
            baseline_results[law_key] = result

    # Calculate each scenario
    scenario_results = {}
    for scenario_idx, scenario_data in sorted(scenarios_data.items()):
        scenario_results[scenario_idx] = {
            "name": scenario_data.get("name", f"Scenario {scenario_idx}"),
            "laws": {},
        }

        for law_info in discoverable_laws:
            service = law_info["service"]
            law = law_info["law"]
            law_key = f"{service}.{law}"

            overwrite_input = scenario_data["overwrites"].get(law_key, {})
            result = calculate_law_with_overwrite(bsn, service, law, overwrite_input, machine_service)

            if result["success"]:
                scenario_results[scenario_idx]["laws"][law_key] = result

    return templates.TemplateResponse(
        "whatif/partials/comparison_results.html",
        {
            "request": request,
            "bsn": bsn,
            "baseline_results": baseline_results,
            "scenario_results": scenario_results,
            "discoverable_laws": discoverable_laws,
        },
    )
