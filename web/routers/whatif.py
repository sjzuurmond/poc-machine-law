"""What-if scenario analysis routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import HTMLResponse

from web.dependencies import TODAY, get_case_manager, get_machine_service, templates
from web.engines.case_manager_interface import CaseManagerInterface
from web.engines.engine_interface import EngineInterface, RuleResult

router = APIRouter(prefix="/whatif", tags=["whatif"])
logger = logging.getLogger(__name__)


def get_fields_from_law_inputs(
    bsn: str, laws: list[tuple[str, str]], machine_service: EngineInterface, focus_keywords: list[str] | None = None
) -> dict[str, Any]:
    """
    Dynamically extract input fields by evaluating laws and inspecting their actual inputs.

    This approach is cleaner than hardcoding field mappings - we let the laws themselves
    tell us what data they need by looking at result.input from actual evaluations.

    Args:
        bsn: The person's BSN for evaluation
        laws: List of (law, service) tuples to evaluate
        machine_service: Engine interface for law evaluation
        focus_keywords: Optional list of keywords to filter fields (e.g., ["inkomen", "vermogen"])

    Returns:
        Dictionary mapping field keys to their current values and metadata:
        {
            'field_key': {
                'value': current_value,
                'label': 'Human readable label',
                'type': 'number' | 'text' | 'select',
            }
        }
    """
    all_inputs = {}

    for law, service in laws:
        try:
            # Evaluate the law to see what inputs it actually uses
            result = machine_service.evaluate(service=service, law=law, parameters={"BSN": bsn}, reference_date=TODAY)

            # result.input contains the actual data the law used
            if result.input:
                # Merge inputs (keeping track of which fields are actually used)
                for field_key, field_value in result.input.items():
                    # Skip BSN and other meta fields
                    if field_key.upper() == "BSN":
                        continue

                    # If focus keywords specified, only include matching fields
                    if focus_keywords and not any(keyword.lower() in field_key.lower() for keyword in focus_keywords):
                        continue

                    if field_key not in all_inputs:
                        all_inputs[field_key] = {
                            "value": field_value,
                            "label": field_key.replace("_", " ").title(),
                            "type": _infer_field_type(field_value),
                        }

        except Exception as e:
            logger.warning(f"Failed to evaluate {law} for field extraction: {e}")

    return all_inputs


def _infer_field_type(value: Any) -> str:
    """Infer HTML input type from value."""
    if isinstance(value, bool):
        return "checkbox"
    elif isinstance(value, (int, float)):
        return "number"
    else:
        return "text"


def create_slider_configs(field_inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Convert dynamic field inputs into slider configurations with intelligent ranges.

    Args:
        field_inputs: Dictionary of field inputs from get_fields_from_law_inputs

    Returns:
        List of slider configurations with min/max/step values
    """
    sliders = []

    for field_key, field_info in field_inputs.items():
        if field_info["type"] != "number":
            continue  # Only create sliders for numeric fields

        current_value = field_info["value"] or 0

        # Determine intelligent ranges based on field name and current value
        if "inkomen" in field_key.lower():
            # Income fields: range from 0 to 2x current (or 100k if current is 0)
            slider_config = {
                "key": field_key,
                "label": field_info["label"],
                "current": current_value,
                "min": 0,
                "max": max(100000, current_value * 2),
                "step": 1000,
                "format": "currency",
            }
        elif "huur" in field_key.lower():
            # Rent fields: monthly rent from 0 to 2500
            slider_config = {
                "key": field_key,
                "label": field_info["label"],
                "current": current_value,
                "min": 0,
                "max": 2500,
                "step": 50,
                "format": "currency_monthly",
            }
        elif "vermogen" in field_key.lower():
            # Vermogen: from 0 to 2x current or 300k
            slider_config = {
                "key": field_key,
                "label": field_info["label"],
                "current": current_value,
                "min": 0,
                "max": max(300000, current_value * 2),
                "step": 5000,
                "format": "currency",
            }
        elif "aow" in field_key.lower() or "pensioen" in field_key.lower():
            # AOW/pension: from 0 to 50k
            slider_config = {
                "key": field_key,
                "label": field_info["label"],
                "current": current_value,
                "min": 0,
                "max": 50000,
                "step": 500,
                "format": "currency",
            }
        else:
            # Generic numeric field
            slider_config = {
                "key": field_key,
                "label": field_info["label"],
                "current": current_value,
                "min": 0,
                "max": max(100, current_value * 2) if current_value > 0 else 1000,
                "step": max(1, int((current_value * 2) / 100)) if current_value > 0 else 10,
                "format": "number",
            }

        sliders.append(slider_config)

    return sliders


def extract_missing_fields(result: RuleResult, machine_service: EngineInterface) -> list[str]:
    """
    Extract the list of missing required field names from the result's path tree.

    Args:
        result: The RuleResult containing the evaluation path
        machine_service: The engine interface for extracting value tree

    Returns:
        List of missing required field names
    """
    missing_fields = []
    if result.missing_required and result.path:
        value_tree = machine_service.extract_value_tree(result.path)

        for path, node_info in value_tree.items():
            if node_info.get("required") and not node_info.get("result"):
                # Get the field name (last part of the path)
                field_name = path.split(".")[-1]
                if field_name not in missing_fields:  # Avoid duplicates
                    missing_fields.append(field_name)

    return missing_fields


def get_primary_output_field(
    result: RuleResult, rule_spec: dict[str, Any], service: str, law: str
) -> dict[str, Any] | None:
    """
    Extract the primary output field from a law evaluation result.

    Looks for output fields marked with citizen_relevance: primary and extracts
    the value along with its type information for proper formatting.

    Args:
        result: The RuleResult from law evaluation
        rule_spec: The rule specification dictionary
        service: Service name (for display)
        law: Law name (for display)

    Returns:
        Dictionary with field info or None if no primary field found:
        {
            'name': field name,
            'value': field value,
            'type': field type (amount, boolean, number, etc),
            'temporal': temporal info (for converting to monthly/yearly),
            'display_name': human-readable name
        }
    """
    if not result.output or not rule_spec:
        return None

    # Get output definitions from rule spec
    output_definitions = rule_spec.get("properties", {}).get("output", [])

    # Find primary output field
    for output_def in output_definitions:
        if output_def.get("citizen_relevance") == "primary":
            field_name = output_def.get("name")
            if field_name and field_name in result.output:
                return {
                    "name": field_name,
                    "value": result.output[field_name],
                    "type": output_def.get("type", "unknown"),
                    "temporal": output_def.get("temporal", {}),
                    "display_name": output_def.get("title") or field_name,
                }

    # Fallback: return first output field if no primary field found
    if result.output:
        first_field = next(iter(result.output.items()))
        return {
            "name": first_field[0],
            "value": first_field[1],
            "type": "unknown",
            "temporal": {},
            "display_name": first_field[0],
        }

    return None


def format_output_value(field_info: dict[str, Any]) -> str:
    """
    Format an output value based on its type.

    Args:
        field_info: Dictionary with field type and value info

    Returns:
        Formatted string representation
    """
    value = field_info["value"]
    field_type = field_info["type"]

    # Handle None/null values
    if value is None:
        return "N/A"

    # Handle boolean values
    if field_type == "boolean":
        return "Ja" if value else "Nee"

    # Handle amounts (monetary values in cents)
    if field_type == "amount" and isinstance(value, (int, float)):
        # Amounts in the system are in cents, convert to euros
        euro_value = value / 100
        return f"€ {euro_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Handle regular numbers
    if field_type == "number":
        if isinstance(value, float):
            return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(value)

    # Handle dates
    if field_type == "date":
        return str(value)

    # Default: return as string
    return str(value)


@router.get("/direct-manipulation", response_class=HTMLResponse)
async def direct_manipulation_panel(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
    case_manager: CaseManagerInterface = Depends(get_case_manager),
) -> HTMLResponse:
    """
    Render the inline direct manipulation panel with sliders.

    Users can adjust values with sliders and see real-time impact.
    """
    try:
        # Get current person data
        person = machine_service.get_profile_data(bsn)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        # Get all cases for this person
        cases = case_manager.get_cases_by_bsn(bsn)

        # Get all discoverable laws for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        # Dynamically extract fields by evaluating laws - much cleaner than hardcoding!
        field_inputs = get_fields_from_law_inputs(bsn, laws_to_check, machine_service, focus_keywords=None)

        # Convert to slider configurations with intelligent ranges
        adjustable_params = create_slider_configs(field_inputs)

        template = templates.get_template("partials/whatif/direct_manipulation.html")
        return HTMLResponse(
            template.render(
                request=request,
                person=person,
                bsn=bsn,
                adjustable_params=adjustable_params,
                cases=cases,
                all_profiles=machine_service.get_all_profiles(),
            )
        )
    except Exception as e:
        logger.error(f"Error loading direct manipulation panel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/direct-manipulation/calculate", response_class=HTMLResponse)
async def calculate_direct_manipulation(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Calculate impact of adjusted parameters in real-time.

    Receives form data with adjusted values and returns updated results.
    """
    try:
        # Get form data
        form_data = await request.form()

        # Build modified person data
        person = machine_service.get_profile_data(bsn)
        modified_person = person.copy()

        # Update with form values
        for key, value in form_data.items():
            if key != "bsn":
                try:
                    modified_person[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    modified_person[key] = value

        # Get discoverable laws sorted by impact for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        results = {}
        for law, service in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                    overwrite_input=modified_person,
                )
                # Extract missing fields if any
                missing_fields = extract_missing_fields(result, machine_service)

                # Get rule spec for type information
                try:
                    rule_spec = machine_service.get_rule_spec(law, TODAY, service)
                    primary_field = get_primary_output_field(result, rule_spec, service, law)
                except Exception as e:
                    logger.warning(f"Failed to get rule spec for {law}: {e}")
                    primary_field = None

                results[law] = {
                    "result": result,
                    "service": service,
                    "missing_fields": missing_fields,
                    "primary_field": primary_field,
                }
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")
                results[law] = {"error": str(e)}

        # Get original results for comparison
        original_results = {}
        for law, service in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                )
                original_results[law] = result
            except Exception as e:
                logger.warning(f"Failed to calculate original {law}: {e}")

        template = templates.get_template("partials/whatif/direct_manipulation_results.html")
        return HTMLResponse(
            template.render(
                request=request,
                results=results,
                original_results=original_results,
                modified_person=modified_person,
            )
        )
    except Exception as e:
        logger.error(f"Error calculating direct manipulation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_class=HTMLResponse)
async def template_scenarios_panel(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Render the template-based scenarios panel.

    Users can choose from pre-defined life scenarios.
    """
    try:
        # Get current person data
        person = machine_service.get_profile_data(bsn)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        # Define scenario templates with focus fields
        # Focus fields define what typically changes in this scenario
        # Additional fields may be added based on which laws are relevant for the user
        scenario_templates = [
            {
                "id": "income_increase",
                "name": "Mijn inkomen verandert",
                "description": "Ik ga meer uren werken of krijg een loonsverhoging. Vul je nieuwe inkomen in en zie het effect op je toeslagen.",
                "icon": "💼",
                "focus_fields": ["inkomen_werk", "inkomen_onderneming"],
            },
            {
                "id": "moving",
                "name": "Ik ga verhuizen",
                "description": "Ik verhuis naar een andere woning. Vul je nieuwe adres en huurprijs in en zie wat dat betekent voor je situatie.",
                "icon": "🏠",
                "focus_fields": ["huur_per_maand", "postcode", "woonplaats"],
            },
            {
                "id": "relationship_change",
                "name": "Ik ga samenwonen/scheiden",
                "description": "Mijn burgerlijke staat verandert. Pas je situatie aan en zie hoe dit je toeslagen beïnvloedt.",
                "icon": "👥",
                "focus_fields": ["burgerlijke_staat", "partner_inkomen"],
            },
            {
                "id": "self_employed",
                "name": "Ik word zelfstandig ondernemer",
                "description": "Ik start als ZZP'er of ondernemer. Vul je verwachte inkomen in en zie hoe dit uitpakt.",
                "icon": "🚀",
                "focus_fields": ["inkomen_onderneming", "inkomen_werk"],
            },
            {
                "id": "retirement",
                "name": "Ik ga met pensioen",
                "description": "Ik stop met werken en krijg AOW/pensioen. Vul je nieuwe situatie in en bereken je inkomsten.",
                "icon": "🌴",
                "focus_fields": ["inkomen_werk", "aow", "pensioen"],
            },
            {
                "id": "custom",
                "name": "Algemeen scenario",
                "description": "Pas alle relevante gegevens aan en zie het totaaleffect op je situatie.",
                "icon": "⚙️",
                "focus_fields": [],  # Empty means show all relevant fields
            },
        ]

        template = templates.get_template("partials/whatif/template_scenarios.html")
        return HTMLResponse(
            template.render(
                request=request,
                person=person,
                bsn=bsn,
                scenario_templates=scenario_templates,
                all_profiles=machine_service.get_all_profiles(),
            )
        )
    except Exception as e:
        logger.error(f"Error loading template scenarios panel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{scenario_id}/form", response_class=HTMLResponse)
async def template_scenario_form(
    request: Request,
    scenario_id: str,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Render the form for a specific scenario template.
    """
    try:
        person = machine_service.get_profile_data(bsn)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        # Define scenario focus keywords - scenarios filter fields by relevance, not hardcode them
        scenario_configs = {
            "income_increase": {"keywords": ["inkomen", "vermogen"]},
            "moving": {"keywords": ["huur", "postcode", "woonplaats", "adres"]},
            "relationship_change": {"keywords": ["burgerlijk", "partner", "gehuwd", "samenwon"]},
            "self_employed": {"keywords": ["inkomen", "onderneming", "zzp"]},
            "retirement": {"keywords": ["aow", "pensioen", "inkomen"]},
            "custom": {"keywords": None},  # None means show all fields
        }

        # Get scenario configuration
        scenario_config = scenario_configs.get(scenario_id, {"keywords": None})
        focus_keywords = scenario_config["keywords"]

        # Get all discoverable laws for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        # Dynamically extract fields by evaluating laws and inspecting their inputs
        # This is much cleaner than hardcoding - we let the laws tell us what they need
        field_inputs = get_fields_from_law_inputs(bsn, laws_to_check, machine_service, focus_keywords)

        # Build field list for template
        fields = [
            {
                "key": field_key,
                "label": field_info["label"],
                "type": field_info["type"],
                "current": field_info["value"],
            }
            for field_key, field_info in field_inputs.items()
        ]

        # Sort fields alphabetically for consistent display
        fields.sort(key=lambda f: f["label"])

        template = templates.get_template("partials/whatif/template_scenario_form.html")
        return HTMLResponse(
            template.render(
                request=request,
                scenario_id=scenario_id,
                bsn=bsn,
                fields=fields,
                person=person,
            )
        )
    except Exception as e:
        logger.error(f"Error loading scenario form: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/calculate", response_class=HTMLResponse)
async def calculate_template_scenario(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Calculate impact of template scenario.
    """
    try:
        form_data = await request.form()

        # Build modified person data
        person = machine_service.get_profile_data(bsn)
        modified_person = person.copy()

        # Update with form values
        for key, value in form_data.items():
            if key not in ["bsn", "scenario_id"]:
                try:
                    # Try to convert to int for numeric fields
                    modified_person[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    # Keep as string for text fields
                    modified_person[key] = value

        # Get discoverable laws sorted by impact for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)

        # Map law names to display names
        display_names = {
            "zorgtoeslagwet": "Zorgtoeslag",
            "wet_op_de_huurtoeslag": "Huurtoeslag",
            "participatiewet": "Participatiewet",
        }

        results = []
        for law_info in discoverable_laws:
            law = law_info["law"]
            service = law_info["service"]
            display_name = display_names.get(law, law)
            try:
                original_result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                )
                new_result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                    overwrite_input=modified_person,
                )

                # Extract main output value
                original_value = _extract_main_value(original_result)
                new_value = _extract_main_value(new_result)

                # Extract missing fields if any
                missing_fields = extract_missing_fields(new_result, machine_service)

                results.append(
                    {
                        "law": law,
                        "display_name": display_name,
                        "service": service,
                        "original": original_result,
                        "original_value": original_value,
                        "new": new_result,
                        "new_value": new_value,
                        "change": new_value - original_value if original_value and new_value else None,
                        "missing_fields": missing_fields,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")

        template = templates.get_template("partials/whatif/template_scenario_results.html")
        return HTMLResponse(
            template.render(
                request=request,
                results=results,
                modified_person=modified_person,
                original_person=person,
            )
        )
    except Exception as e:
        logger.error(f"Error calculating template scenario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison", response_class=HTMLResponse)
async def comparison_panel(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Render the comparison mode panel for side-by-side scenario comparison.
    """
    try:
        # Get current person data
        person = machine_service.get_profile_data(bsn)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        # Calculate current baseline
        laws_to_check = [
            ("zorgtoeslagwet", "TOESLAGEN", "Zorgtoeslag"),
            ("wet_op_de_huurtoeslag", "TOESLAGEN", "Huurtoeslag"),
            ("participatiewet", "GEMEENTE", "Participatiewet"),
        ]

        current_results = []
        for law, service, display_name in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                )
                value = _extract_main_value(result)
                current_results.append(
                    {
                        "law": law,
                        "display_name": display_name,
                        "value": value,
                        "result": result,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")

        template = templates.get_template("partials/whatif/comparison.html")
        return HTMLResponse(
            template.render(
                request=request,
                person=person,
                bsn=bsn,
                current_results=current_results,
                all_profiles=machine_service.get_all_profiles(),
            )
        )
    except Exception as e:
        logger.error(f"Error loading comparison panel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comparison/add-scenario", response_class=HTMLResponse)
async def add_comparison_scenario(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Add a new scenario to the comparison view.
    """
    try:
        form_data = await request.form()
        scenario_name = form_data.get("scenario_name", "Nieuw scenario")

        # Build modified person data
        person = machine_service.get_profile_data(bsn)
        modified_person = person.copy()

        # Update with form values
        for key, value in form_data.items():
            if key not in ["bsn", "scenario_name"]:
                try:
                    modified_person[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    modified_person[key] = value

        # Calculate law results
        laws_to_check = [
            ("zorgtoeslagwet", "TOESLAGEN", "Zorgtoeslag"),
            ("wet_op_de_huurtoeslag", "TOESLAGEN", "Huurtoeslag"),
            ("participatiewet", "GEMEENTE", "Participatiewet"),
        ]

        scenario_results = []
        for law, service, display_name in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                    overwrite_input=modified_person,
                )
                value = _extract_main_value(result)
                scenario_results.append(
                    {
                        "law": law,
                        "display_name": display_name,
                        "value": value,
                        "result": result,
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")

        # Calculate key parameter changes
        param_changes = {}
        for key in ["inkomen_werk", "huur_per_maand", "inkomen_onderneming", "vermogen"]:
            original = person.get(key, 0)
            new = modified_person.get(key, 0)
            if original != new:
                param_changes[key] = {"original": original, "new": new}

        template = templates.get_template("partials/whatif/comparison_scenario_column.html")
        return HTMLResponse(
            template.render(
                request=request,
                scenario_name=scenario_name,
                scenario_results=scenario_results,
                param_changes=param_changes,
                modified_person=modified_person,
            )
        )
    except Exception as e:
        logger.error(f"Error adding comparison scenario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variations/compact", response_class=HTMLResponse)
async def compact_variation(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Render the compact side-by-side variation.

    Exact implementation of the ASCII art specification.
    """
    try:
        person = machine_service.get_profile_data(bsn)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        template = templates.get_template("partials/whatif/variations/compact_sidebyside.html")
        return HTMLResponse(
            template.render(
                request=request,
                person=person,
                bsn=bsn,
                all_profiles=machine_service.get_all_profiles(),
            )
        )
    except Exception as e:
        logger.error(f"Error loading compact variation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variations/fullscreen", response_class=HTMLResponse)
async def fullscreen_variation(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Render the full-screen interactive variation.

    Rich visual experience with gradient cards and detailed feedback.
    """
    try:
        person = machine_service.get_profile_data(bsn)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        template = templates.get_template("partials/whatif/variations/fullscreen_interactive.html")
        return HTMLResponse(
            template.render(
                request=request,
                person=person,
                bsn=bsn,
                all_profiles=machine_service.get_all_profiles(),
            )
        )
    except Exception as e:
        logger.error(f"Error loading fullscreen variation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variations/compact/calculate", response_class=HTMLResponse)
async def calculate_compact_variation(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """Calculate results for compact variation."""
    try:
        form_data = await request.form()
        person = machine_service.get_profile_data(bsn)
        modified_person = person.copy()

        for key, value in form_data.items():
            if key != "bsn":
                try:
                    modified_person[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    modified_person[key] = value

        # Get discoverable laws sorted by impact for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        results = {}
        original_results = {}
        for law, service in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                    overwrite_input=modified_person,
                )
                # Extract missing fields if any
                missing_fields = extract_missing_fields(result, machine_service)

                results[law] = {
                    "result": result,
                    "service": service,
                    "missing_fields": missing_fields,
                }
                original_result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                )
                original_results[law] = original_result
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")

        template = templates.get_template("partials/whatif/variations/compact_results.html")
        return HTMLResponse(
            template.render(
                request=request,
                results=results,
                original_results=original_results,
                modified_person=modified_person,
            )
        )
    except Exception as e:
        logger.error(f"Error calculating compact variation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variations/widget/calculate", response_class=HTMLResponse)
async def calculate_widget_variation(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """Calculate results for widget variation."""
    try:
        form_data = await request.form()
        person = machine_service.get_profile_data(bsn)
        modified_person = person.copy()

        for key, value in form_data.items():
            if key != "bsn":
                try:
                    modified_person[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    modified_person[key] = value

        # Get discoverable laws sorted by impact for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        results = {}
        original_results = {}
        for law, service in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                    overwrite_input=modified_person,
                )
                # Extract missing fields if any
                missing_fields = extract_missing_fields(result, machine_service)

                results[law] = {
                    "result": result,
                    "service": service,
                    "missing_fields": missing_fields,
                }
                original_result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                )
                original_results[law] = original_result
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")

        template = templates.get_template("partials/whatif/variations/widget_results.html")
        return HTMLResponse(
            template.render(
                request=request,
                results=results,
                original_results=original_results,
                modified_person=modified_person,
            )
        )
    except Exception as e:
        logger.error(f"Error calculating widget variation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variations/fullscreen/calculate", response_class=HTMLResponse)
async def calculate_fullscreen_variation(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """Calculate results for fullscreen variation."""
    try:
        form_data = await request.form()
        person = machine_service.get_profile_data(bsn)
        modified_person = person.copy()

        for key, value in form_data.items():
            if key != "bsn":
                try:
                    modified_person[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    modified_person[key] = value

        # Get discoverable laws sorted by impact for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        results = {}
        original_results = {}
        for law, service in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                    overwrite_input=modified_person,
                )
                # Extract missing fields if any
                missing_fields = extract_missing_fields(result, machine_service)

                results[law] = {
                    "result": result,
                    "service": service,
                    "missing_fields": missing_fields,
                }
                original_result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                )
                original_results[law] = original_result
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")

        template = templates.get_template("partials/whatif/variations/fullscreen_results.html")
        return HTMLResponse(
            template.render(
                request=request,
                results=results,
                original_results=original_results,
                modified_person=modified_person,
            )
        )
    except Exception as e:
        logger.error(f"Error calculating fullscreen variation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/variations/modal/calculate", response_class=HTMLResponse)
async def calculate_modal_variation(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """Calculate results for modal variation."""
    try:
        form_data = await request.form()
        person = machine_service.get_profile_data(bsn)
        modified_person = person.copy()

        for key, value in form_data.items():
            if key != "bsn":
                try:
                    modified_person[key] = int(value) if value else 0
                except (ValueError, TypeError):
                    modified_person[key] = value

        # Get discoverable laws sorted by impact for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        results = {}
        original_results = {}
        for law, service in laws_to_check:
            try:
                result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                    overwrite_input=modified_person,
                )
                # Extract missing fields if any
                missing_fields = extract_missing_fields(result, machine_service)

                results[law] = {
                    "result": result,
                    "service": service,
                    "missing_fields": missing_fields,
                }
                original_result = machine_service.evaluate(
                    service=service,
                    law=law,
                    parameters={"BSN": bsn},
                    reference_date=TODAY,
                )
                original_results[law] = original_result
            except Exception as e:
                logger.warning(f"Failed to calculate {law}: {e}")

        template = templates.get_template("partials/whatif/variations/modal_results.html")
        return HTMLResponse(
            template.render(
                request=request,
                results=results,
                original_results=original_results,
                modified_person=modified_person,
            )
        )
    except Exception as e:
        logger.error(f"Error calculating modal variation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _extract_main_value(result: Any) -> float | None:
    """Extract the main monetary value from a law result."""
    if not result or not hasattr(result, "output"):
        return None

    output = result.output

    # Try common output keys
    for key in [
        "totale_zorgtoeslag_per_maand",
        "totale_huurtoeslag_per_maand",
        "bijstand_per_maand",
        "toeslag",
        "uitkering",
        "bedrag",
    ]:
        if key in output:
            value = output[key]
            if isinstance(value, (int, float)):
                return float(value)

    return None
