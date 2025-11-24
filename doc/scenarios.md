# Scenario System Documentation

## Overview

The scenario system allows users to perform "what-if" calculations by temporarily overriding input values without creating persistent claims in the database. This is perfect for exploring how changes would affect law outcomes before committing to an official change request.

## Architecture

### Components

```
web/
├── models/
│   └── scenario.py          # Data models (Scenario, ScenarioValue, ScenarioManager)
├── helpers/
│   └── scenario_helpers.py  # Integration helpers
├── routers/
│   ├── scenarios.py         # Scenario endpoints
│   └── laws.py              # Updated with scenario support
└── templates/partials/
    ├── scenario_panel.html       # Scenario status/controls
    ├── scenario_form.html        # Add/edit scenario value
    ├── scenario_comparison.html  # Side-by-side comparison
    └── scenario_value_added.html # Success message
```

### Data Flow

```
User Input (Frontend)
    ↓
Scenario Router (/scenarios/value/set)
    ↓
ScenarioManager (Session Storage)
    ↓
evaluate_law() with use_scenarios=True
    ↓
get_evaluation_overrides() (Helper)
    ↓
RulesEngine with overwrite_input
    ↓
Updated Calculation Results
```

## Key Features

### 1. **Session-Based Storage**

Scenarios are stored in the user's session, not in the database:
- No database writes
- Automatically cleaned on logout
- User-specific (no cross-contamination)
- Fast access

### 2. **Type-Aware Parsing**

The system automatically detects and parses value types:
- Booleans: `"true"`, `"false"`
- Numbers: `"42"`, `"3.14"`
- Dates: `"2025-01-01"`
- Arrays: `"[1, 2, 3]"`
- Objects: `'{"key": "value"}'`

### 3. **Smart Comparison**

The comparison view shows:
- Official baseline values
- Scenario values
- Calculated differences
- Visual indicators (green/red for positive/negative changes)
- Requirements check for both scenarios

### 4. **Conversion to Claims**

Users can convert satisfied scenarios to official claims:
```python
POST /scenarios/convert-to-claims
```

This creates claims for all scenario values and clears the scenario.

## Usage

### Frontend Integration

#### 1. Check if Scenarios Active

```html
{% if scenario_active %}
    {% include "partials/scenario_panel.html" %}
{% endif %}
```

#### 2. Enable Scenario Mode

Add `use_scenarios=true` parameter to law execution:

```html
<div hx-get="/laws/execute?bsn={{ bsn }}&service={{ service }}&law={{ law }}&use_scenarios=true"
     hx-trigger="load">
</div>
```

#### 3. Add Scenario Value

```html
<button hx-get="/scenarios/form?bsn={{ bsn }}&service={{ service }}&law={{ law }}&key=income&current_value=30000"
        hx-target="#modal-container">
    🧪 Test andere waarde
</button>
```

### Backend Integration

#### Update evaluate_law Calls

```python
from web.helpers.scenario_helpers import get_evaluation_overrides

def evaluate_law(
    bsn: str,
    law: str,
    service: str,
    machine_service: EngineInterface,
    request: Request | None = None,
    use_scenarios: bool = False,
    scenario_name: str = "default",
):
    # Get overrides from scenarios
    overwrite_input = get_evaluation_overrides(
        request=request,
        bsn=bsn,
        service=service,
        law=law,
        approved=False,
        claim_manager=claim_manager,
        use_scenarios=use_scenarios,
        scenario_name=scenario_name,
    )

    # Evaluate with overrides
    result = machine_service.evaluate(
        service=service,
        law=law,
        parameters={"BSN": bsn},
        overwrite_input=overwrite_input,
        ...
    )
```

## API Reference

### Endpoints

#### `POST /scenarios/value/set`

Set a scenario value.

**Parameters:**
- `bsn`: BSN of the person
- `service`: Service name
- `law`: Law name
- `key`: Field name to override
- `value`: New value (as string, will be parsed)
- `label`: Optional display label
- `type_hint`: Optional type hint (`boolean`, `number`, `date`, `array`, `string`)
- `scenario_name`: Name of scenario (default: "default")

**Response:** HTML fragment with success message + HX-Trigger

---

#### `GET /scenarios/list`

Get all scenarios for a BSN.

**Parameters:**
- `bsn`: BSN of the person

**Response:**
```json
{
    "status": "success",
    "scenarios": [...],
    "count": 1
}
```

---

#### `DELETE /scenarios/value/delete`

Delete a specific scenario value.

**Parameters:**
- `bsn`: BSN
- `service`: Service name
- `law`: Law name
- `key`: Field name
- `scenario_name`: Scenario name

---

#### `POST /scenarios/clear`

Clear all values from a scenario.

**Parameters:**
- `bsn`: BSN
- `scenario_name`: Scenario name

---

#### `POST /scenarios/convert-to-claims`

Convert all scenario values to official claims.

**Parameters:**
- `bsn`: BSN
- `scenario_name`: Scenario name
- `reason`: Reason for the claims

**Response:**
```json
{
    "status": "success",
    "claim_ids": ["uuid1", "uuid2"],
    "claim_count": 2
}
```

---

#### `GET /scenarios/compare`

Compare outcomes with and without scenarios.

**Parameters:**
- `bsn`: BSN
- `service`: Service name
- `law`: Law name

**Response:** HTML comparison table

## Data Models

### ScenarioValue

```python
@dataclass
class ScenarioValue:
    service: str
    law: str
    key: str
    value: Any
    label: str | None
    timestamp: datetime
```

### Scenario

```python
@dataclass
class Scenario:
    name: str
    bsn: str
    values: dict[str, ScenarioValue]
    description: str
    created_at: datetime
    updated_at: datetime

    def get_overwrite_input(self) -> dict[str, dict[str, Any]]:
        """Convert to engine format"""
```

### ScenarioManager

Session-based CRUD operations:
- `get_or_create(session, bsn, name)`
- `save(session, scenario)`
- `delete(session, bsn, name)`
- `list_scenarios(session, bsn)`
- `clear_all(session, bsn)`

## Configuration

### Session Middleware

Ensure session middleware is configured:

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY"),
    max_age=3600,  # 1 hour
    same_site="lax",
)
```

### Router Registration

Register the scenarios router:

```python
from web.routers import scenarios

app.include_router(scenarios.router)
```

## Best Practices

### 1. **Clear Communication**

Always show users that they're in scenario mode:
- Visual indicators (purple/blue theme)
- "🧪" emoji for scenario features
- Clear messaging about temporary nature

### 2. **Comparison Before Conversion**

Encourage users to review comparison before converting to claims:
```html
<button hx-get="/scenarios/compare">
    📊 Bekijk verschil eerst
</button>
```

### 3. **Validation**

Validate scenario values match expected types:
```python
parsed_value = parse_value(value_str, type_hint)
```

### 4. **Cleanup**

Scenarios auto-cleanup on logout, but provide manual clear:
```html
<button hx-post="/scenarios/clear">
    Scenario wissen
</button>
```

## Comparison with Claims

| Aspect | Scenarios | Claims |
|--------|-----------|--------|
| **Storage** | Session (temporary) | Database (persistent) |
| **Lifespan** | Until logout | Until approved/rejected |
| **Approval** | None needed | Required workflow |
| **Audit Trail** | None | Full event sourcing |
| **Use Case** | Exploration/"what-if" | Official change requests |
| **Performance** | Fast (memory) | Slower (I/O) |
| **Shareable** | No | Yes (via case ID) |
| **Reversible** | Instant | Workflow-dependent |

## Troubleshooting

### Scenarios Not Persisting

**Problem:** Scenarios disappear on page refresh
**Solution:** Check session middleware is configured and secret key is set

### Wrong Values Used

**Problem:** Official values used instead of scenarios
**Solution:** Ensure `use_scenarios=true` parameter is passed to `/laws/execute`

### Type Parsing Issues

**Problem:** Values not parsed correctly
**Solution:** Provide explicit `type_hint` parameter in form

## Future Enhancements

- [ ] Named scenarios (save multiple scenarios per user)
- [ ] Scenario templates (predefined test scenarios)
- [ ] Scenario sharing (export/import)
- [ ] Scenario history (undo/redo)
- [ ] Bulk scenario operations
- [ ] Scenario recommendations (AI-powered)
