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


def get_all_known_data_with_sources(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract all known data about the user with source information.

    Returns a list of data items with their values and sources for display.

    Args:
        profile: Nested profile dictionary from get_profile_data()

    Returns:
        List of dictionaries with format:
        [{
            'category': 'Persoonlijke gegevens',
            'label': 'Geboortedatum',
            'value': '1989-05-15',
            'source': 'RvIG',
            'field_key': 'geboortedatum',
            'editable': False
        }, ...]
    """
    data_items = []

    if not profile or "sources" not in profile:
        return data_items

    sources = profile["sources"]

    # Personal data from RvIG
    if "RvIG" in sources:
        if "personen" in sources["RvIG"] and sources["RvIG"]["personen"]:
            person = sources["RvIG"]["personen"][0]

            data_items.append(
                {
                    "category": "Persoonlijke gegevens",
                    "label": "BSN",
                    "value": person.get("bsn", "Onbekend"),
                    "source": "RvIG - Basisregistratie Personen",
                    "field_key": "bsn",
                    "editable": False,
                }
            )

            data_items.append(
                {
                    "category": "Persoonlijke gegevens",
                    "label": "Geboortedatum",
                    "value": person.get("geboortedatum", "Onbekend"),
                    "source": "RvIG - Basisregistratie Personen",
                    "field_key": "geboortedatum",
                    "editable": False,
                }
            )

            data_items.append(
                {
                    "category": "Persoonlijke gegevens",
                    "label": "Leeftijd",
                    "value": f"{person.get('age', 'Onbekend')} jaar",
                    "source": "RvIG - Berekend",
                    "field_key": "age",
                    "editable": False,
                }
            )

            data_items.append(
                {
                    "category": "Persoonlijke gegevens",
                    "label": "Nationaliteit",
                    "value": person.get("nationaliteit", "Onbekend"),
                    "source": "RvIG - Basisregistratie Personen",
                    "field_key": "nationaliteit",
                    "editable": False,
                }
            )

        # Address data
        if "verblijfplaats" in sources["RvIG"] and sources["RvIG"]["verblijfplaats"]:
            address = sources["RvIG"]["verblijfplaats"][0]

            full_address = f"{address.get('straat', '')} {address.get('huisnummer', '')}, {address.get('postcode', '')} {address.get('woonplaats', '')}"
            data_items.append(
                {
                    "category": "Woongegevens",
                    "label": "Adres",
                    "value": full_address.strip(),
                    "source": "RvIG - Basisregistratie Adressen",
                    "field_key": "adres",
                    "editable": False,
                }
            )

            data_items.append(
                {
                    "category": "Woongegevens",
                    "label": "Postcode",
                    "value": address.get("postcode", "Onbekend"),
                    "source": "RvIG",
                    "field_key": "postcode",
                    "editable": True,
                }
            )

            data_items.append(
                {
                    "category": "Woongegevens",
                    "label": "Woonplaats",
                    "value": address.get("woonplaats", "Onbekend"),
                    "source": "RvIG",
                    "field_key": "woonplaats",
                    "editable": True,
                }
            )

        # Relationship status
        if "relaties" in sources["RvIG"] and sources["RvIG"]["relaties"]:
            relaties = sources["RvIG"]["relaties"][0]
            partnerschap = relaties.get("partnerschap_type", "GEEN")

            # Map to Dutch
            status_map = {
                "GEHUWD": "Gehuwd",
                "SAMENWONEND": "Samenwonend",
                "GESCHEIDEN": "Gescheiden",
                "GEEN": "Alleenstaand",
            }

            data_items.append(
                {
                    "category": "Gezinssituatie",
                    "label": "Burgerlijke staat",
                    "value": status_map.get(partnerschap, partnerschap),
                    "source": "RvIG - Basisregistratie Personen",
                    "field_key": "burgerlijke_staat",
                    "editable": True,
                }
            )

            if "kinderen" in relaties and relaties["kinderen"]:
                data_items.append(
                    {
                        "category": "Gezinssituatie",
                        "label": "Aantal kinderen",
                        "value": str(len(relaties["kinderen"])),
                        "source": "RvIG - Basisregistratie Personen",
                        "field_key": "aantal_kinderen",
                        "editable": False,
                    }
                )

    # Income data from Belastingdienst
    if "BELASTINGDIENST" in sources:
        if "box1" in sources["BELASTINGDIENST"] and sources["BELASTINGDIENST"]["box1"]:
            box1 = sources["BELASTINGDIENST"]["box1"][0]

            loon = box1.get("loon_uit_dienstbetrekking", 0)
            if loon > 0:
                data_items.append(
                    {
                        "category": "Inkomen",
                        "label": "Loon uit dienstbetrekking",
                        "value": f"€ {loon:,.0f}".replace(",", "."),
                        "source": "Belastingdienst - Box 1",
                        "field_key": "inkomen_werk",
                        "editable": True,
                    }
                )

            onderneming = box1.get("winst_uit_onderneming", 0)
            if onderneming > 0:
                data_items.append(
                    {
                        "category": "Inkomen",
                        "label": "Winst uit onderneming",
                        "value": f"€ {onderneming:,.0f}".replace(",", "."),
                        "source": "Belastingdienst - Box 1",
                        "field_key": "inkomen_onderneming",
                        "editable": True,
                    }
                )

        # Assets/vermogen
        if (
            "belastingdienst_vermogen" in sources["BELASTINGDIENST"]
            and sources["BELASTINGDIENST"]["belastingdienst_vermogen"]
        ):
            vermogen_data = sources["BELASTINGDIENST"]["belastingdienst_vermogen"][0]
            vermogen = vermogen_data.get("vermogen", 0)
            if vermogen > 0:
                data_items.append(
                    {
                        "category": "Vermogen",
                        "label": "Spaargeld en bezittingen",
                        "value": f"€ {vermogen:,.0f}".replace(",", "."),
                        "source": "Belastingdienst - Vermogen",
                        "field_key": "vermogen",
                        "editable": True,
                    }
                )

    # Rent data from Toeslagen
    if "TOESLAGEN" in sources:
        if "huur_en_woongegevens" in sources["TOESLAGEN"] and sources["TOESLAGEN"]["huur_en_woongegevens"]:
            huur_data = sources["TOESLAGEN"]["huur_en_woongegevens"][0]
            huurprijs = huur_data.get("huurprijs", 0)
            if huurprijs > 0:
                huur_per_maand = huurprijs / 12
                data_items.append(
                    {
                        "category": "Woongegevens",
                        "label": "Huur per maand",
                        "value": f"€ {huur_per_maand:,.0f}".replace(",", "."),
                        "source": "Toeslagen - Huurgegevens",
                        "field_key": "huur_per_maand",
                        "editable": True,
                    }
                )

    return data_items


def extract_whatif_parameters(profile: dict[str, Any]) -> dict[str, Any]:
    """
    Extract commonly adjusted parameters from nested profile structure.

    Maps nested profile data to flat dictionary of adjustable parameters.

    Args:
        profile: Nested profile dictionary from get_profile_data()

    Returns:
        Flattened dictionary with common adjustable parameters
    """
    params = {}

    if not profile or "sources" not in profile:
        return params

    sources = profile["sources"]

    # Extract income from work (loon_uit_dienstbetrekking)
    if "BELASTINGDIENST" in sources and "box1" in sources["BELASTINGDIENST"]:
        box1_data = sources["BELASTINGDIENST"]["box1"]
        if box1_data:
            params["inkomen_werk"] = box1_data[0].get("loon_uit_dienstbetrekking", 0)
            params["inkomen_onderneming"] = box1_data[0].get("winst_uit_onderneming", 0)

    # Extract assets/vermogen
    if "BELASTINGDIENST" in sources:
        if "belastingdienst_vermogen" in sources["BELASTINGDIENST"]:
            vermogen_data = sources["BELASTINGDIENST"]["belastingdienst_vermogen"]
            if vermogen_data:
                params["vermogen"] = vermogen_data[0].get("vermogen", 0)
        elif "box3" in sources["BELASTINGDIENST"]:
            box3_data = sources["BELASTINGDIENST"]["box3"]
            if box3_data:
                params["vermogen"] = box3_data[0].get("spaargeld", 0)

    # Extract rent (huur_per_maand) - check TOESLAGEN or other sources
    if "TOESLAGEN" in sources:
        if "huur_en_woongegevens" in sources["TOESLAGEN"]:
            huur_data = sources["TOESLAGEN"]["huur_en_woongegevens"]
            if huur_data:
                # Extract from huurprijs (yearly) and convert to monthly
                huurprijs = huur_data[0].get("huurprijs", 0)
                params["huur_per_maand"] = huurprijs / 12 if huurprijs else 0
        elif "huurtoeslag_woongegevens" in sources["TOESLAGEN"]:
            woon_data = sources["TOESLAGEN"]["huurtoeslag_woongegevens"]
            if woon_data:
                huurprijs = woon_data[0].get("huurprijs", 0)
                params["huur_per_maand"] = huurprijs / 12 if huurprijs else 0

    # Extract partner income if applicable
    if "BELASTINGDIENST" in sources and "partner_inkomen" in sources["BELASTINGDIENST"]:
        partner_data = sources["BELASTINGDIENST"]["partner_inkomen"]
        if partner_data:
            params["partner_inkomen"] = partner_data[0].get("inkomen", 0)

    # Extract address information (postcode, woonplaats)
    if "RvIG" in sources and "verblijfplaats" in sources["RvIG"]:
        verblijf_data = sources["RvIG"]["verblijfplaats"]
        if verblijf_data:
            params["postcode"] = verblijf_data[0].get("postcode", "")
            params["woonplaats"] = verblijf_data[0].get("woonplaats", "")

    # Extract relationship status (burgerlijke_staat)
    if "RvIG" in sources and "relaties" in sources["RvIG"]:
        relatie_data = sources["RvIG"]["relaties"]
        if relatie_data:
            partnerschap_type = relatie_data[0].get("partnerschap_type", "GEEN")
            # Map partnerschap_type to burgerlijke_staat
            if partnerschap_type == "GEHUWD":
                params["burgerlijke_staat"] = "gehuwd"
            elif partnerschap_type == "SAMENWONEND":
                params["burgerlijke_staat"] = "samenwonend"
            elif partnerschap_type == "GESCHEIDEN":
                params["burgerlijke_staat"] = "gescheiden"
            else:
                params["burgerlijke_staat"] = "alleenstaand"

    # Extract AOW and pension (if available in profile)
    # These are typically not in the profile data yet, but we add extraction logic for future use
    if "BELASTINGDIENST" in sources and "box1" in sources["BELASTINGDIENST"]:
        box1_data = sources["BELASTINGDIENST"]["box1"]
        if box1_data:
            params["aow"] = box1_data[0].get("uitkeringen_en_pensioenen", 0)
            params["pensioen"] = box1_data[0].get("pensioen", 0)

    return params


def get_law_required_fields(laws: list[tuple[str, str]], machine_service: EngineInterface) -> dict[str, dict]:
    """
    Get the required input fields for a set of laws.

    This function maps laws to their required input fields. Currently uses a pragmatic
    mapping based on known law requirements. Can be extended to parse rule specifications
    dynamically from the machine service.

    Args:
        laws: List of (law, service) tuples
        machine_service: Engine interface (for future dynamic field extraction)

    Returns:
        Dictionary mapping field keys to field configurations:
        {
            'field_key': {
                'label': 'Human readable label',
                'type': 'number' | 'text' | 'select',
                'placeholder': 'Example value',
                'options': [...] (for select fields)
            }
        }
    """
    # Mapping of law names to their required input fields
    # This is a pragmatic approach - can be extended to parse from rule specs
    LAW_FIELD_REQUIREMENTS = {
        "zorgtoeslagwet": ["inkomen_werk", "vermogen", "burgerlijke_staat"],
        "wet_op_de_huurtoeslag": ["huur_per_maand", "inkomen_werk", "postcode", "woonplaats"],
        "participatiewet": ["inkomen_werk", "vermogen", "burgerlijke_staat"],
        "wet_inkomstenbelasting_2001": ["inkomen_werk", "inkomen_onderneming", "vermogen"],
        "algemene_ouderdomswet": ["aow", "pensioen", "inkomen_werk"],
    }

    # Field configuration templates
    FIELD_CONFIGS = {
        "inkomen_werk": {
            "label": "Inkomen uit werk (per jaar)",
            "type": "number",
            "placeholder": "Bijv. 35000",
        },
        "inkomen_onderneming": {
            "label": "Inkomen uit onderneming (per jaar)",
            "type": "number",
            "placeholder": "Bijv. 40000",
        },
        "vermogen": {
            "label": "Vermogen (spaargeld en bezittingen)",
            "type": "number",
            "placeholder": "Bijv. 50000",
        },
        "huur_per_maand": {
            "label": "Huur per maand",
            "type": "number",
            "placeholder": "Bijv. 750",
        },
        "postcode": {
            "label": "Postcode",
            "type": "text",
            "placeholder": "Bijv. 1012AB",
        },
        "woonplaats": {
            "label": "Woonplaats",
            "type": "text",
            "placeholder": "Bijv. Amsterdam",
        },
        "burgerlijke_staat": {
            "label": "Burgerlijke staat",
            "type": "select",
            "options": ["alleenstaand", "gehuwd", "samenwonend", "gescheiden"],
        },
        "partner_inkomen": {
            "label": "Inkomen partner (per jaar)",
            "type": "number",
            "placeholder": "Bijv. 30000",
        },
        "aow": {
            "label": "AOW (per jaar)",
            "type": "number",
            "placeholder": "Bijv. 14000",
        },
        "pensioen": {
            "label": "Pensioen (per jaar)",
            "type": "number",
            "placeholder": "Bijv. 20000",
        },
    }

    # Collect all required fields from the laws
    required_fields = set()
    for law, service in laws:
        if law in LAW_FIELD_REQUIREMENTS:
            required_fields.update(LAW_FIELD_REQUIREMENTS[law])

    # Build field configuration dictionary
    fields_config = {}
    for field_key in required_fields:
        if field_key in FIELD_CONFIGS:
            fields_config[field_key] = FIELD_CONFIGS[field_key].copy()

    return fields_config


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

        # Extract flattened parameters for whatif adjustments
        current_params = extract_whatif_parameters(person)

        # Get all cases for this person
        cases = case_manager.get_cases_by_bsn(bsn)

        # Define the main adjustable parameters with their ranges
        adjustable_params = [
            {
                "key": "inkomen_werk",
                "label": "Inkomen uit werk",
                "current": current_params.get("inkomen_werk", 0),
                "min": 0,
                "max": 80000,
                "step": 1000,
                "format": "currency",
            },
            {
                "key": "huur_per_maand",
                "label": "Huur per maand",
                "current": current_params.get("huur_per_maand", 0),
                "min": 0,
                "max": 2000,
                "step": 50,
                "format": "currency_monthly",
            },
            {
                "key": "inkomen_onderneming",
                "label": "Inkomen uit onderneming",
                "current": current_params.get("inkomen_onderneming", 0),
                "min": 0,
                "max": 100000,
                "step": 1000,
                "format": "currency",
            },
            {
                "key": "vermogen",
                "label": "Vermogen",
                "current": current_params.get("vermogen", 0),
                "min": 0,
                "max": 200000,
                "step": 5000,
                "format": "currency",
            },
        ]

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

        # Extract current values from nested profile structure
        current_values = extract_whatif_parameters(person)

        # Define scenario configurations with focus fields
        scenario_configs = {
            "income_increase": {
                "focus_fields": ["inkomen_werk", "inkomen_onderneming"],
            },
            "moving": {
                "focus_fields": ["huur_per_maand", "postcode", "woonplaats"],
            },
            "relationship_change": {
                "focus_fields": ["burgerlijke_staat", "partner_inkomen"],
            },
            "self_employed": {
                "focus_fields": ["inkomen_onderneming", "inkomen_werk"],
            },
            "retirement": {
                "focus_fields": ["inkomen_werk", "aow", "pensioen"],
            },
            "custom": {
                "focus_fields": [],  # Empty means show all relevant fields
            },
        }

        # Get scenario configuration
        scenario_config = scenario_configs.get(scenario_id, {"focus_fields": []})
        focus_fields = scenario_config["focus_fields"]

        # Get all discoverable laws for this person
        discoverable_laws = machine_service.get_sorted_discoverable_service_laws(bsn)
        laws_to_check = [(law_info["law"], law_info["service"]) for law_info in discoverable_laws]

        # Get all required fields based on relevant laws
        all_fields_config = get_law_required_fields(laws_to_check, machine_service)

        # Determine which fields to show:
        # - If focus_fields is empty (custom scenario), show all fields
        # - Otherwise, show focus_fields + any additional fields required by laws
        if focus_fields:
            # Start with focus fields
            fields_to_show = set(focus_fields)

            # Add any law-required fields that overlap with focus areas
            # This ensures we don't miss critical fields for laws affected by the scenario
            for field_key in all_fields_config:
                # If this field is needed by any relevant law AND is in our focus area, include it
                if field_key in focus_fields or any(
                    keyword in field_key
                    for keyword in [
                        "inkomen",
                        "vermogen",
                        "huur",
                        "postcode",
                        "woonplaats",
                        "burgerlijk",
                        "partner",
                        "aow",
                        "pensioen",
                    ]
                ):
                    # Only add if it's contextually relevant to the scenario
                    if (
                        scenario_id == "moving"
                        and field_key in ["huur_per_maand", "postcode", "woonplaats"]
                        or scenario_id == "income_increase"
                        and "inkomen" in field_key
                        or scenario_id == "relationship_change"
                        and ("burgerlijk" in field_key or "partner" in field_key)
                        or scenario_id == "self_employed"
                        and "inkomen" in field_key
                        or scenario_id == "retirement"
                        and (field_key in ["inkomen_werk", "aow", "pensioen"])
                        or field_key in focus_fields
                    ):
                        fields_to_show.add(field_key)
        else:
            # Custom scenario: show all relevant fields
            fields_to_show = set(all_fields_config.keys())

        # Build field list with current values
        fields = []
        for field_key in fields_to_show:
            if field_key in all_fields_config:
                field_config = all_fields_config[field_key]
                field = {
                    "key": field_key,
                    "label": field_config["label"],
                    "type": field_config["type"],
                    "current": current_values.get(field_key, 0 if field_config["type"] == "number" else ""),
                    "placeholder": field_config.get("placeholder", ""),
                }
                if "options" in field_config:
                    field["options"] = field_config["options"]

                fields.append(field)

        # Sort fields for consistent display (income first, then other fields)
        field_order = [
            "inkomen_werk",
            "inkomen_onderneming",
            "vermogen",
            "huur_per_maand",
            "postcode",
            "woonplaats",
            "burgerlijke_staat",
            "partner_inkomen",
            "aow",
            "pensioen",
        ]
        fields.sort(key=lambda f: field_order.index(f["key"]) if f["key"] in field_order else 999)

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


@router.get("/data-overview", response_class=HTMLResponse)
async def data_overview_panel(
    request: Request,
    bsn: str,
    machine_service: EngineInterface = Depends(get_machine_service),
) -> HTMLResponse:
    """
    Render a panel showing all known data about the user with sources.
    """
    try:
        person = machine_service.get_profile_data(bsn)
        if not person:
            raise HTTPException(status_code=404, detail="Person not found")

        # Get all known data with sources
        all_data = get_all_known_data_with_sources(person)

        # Group by category
        grouped_data = {}
        for item in all_data:
            category = item["category"]
            if category not in grouped_data:
                grouped_data[category] = []
            grouped_data[category].append(item)

        template = templates.get_template("partials/whatif/data_overview.html")
        return HTMLResponse(
            template.render(
                request=request,
                bsn=bsn,
                grouped_data=grouped_data,
            )
        )
    except Exception as e:
        logger.error(f"Error loading data overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
