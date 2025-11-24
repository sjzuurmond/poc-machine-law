# Test Suite for Scenario System

This directory contains comprehensive tests for the scenario "what-if" calculation system.

## Test Structure

```
tests/
├── unit/                           # Unit tests (fast, no dependencies)
│   ├── test_scenario_models.py    # Tests for Scenario, ScenarioValue, ScenarioManager
│   └── test_scenario_helpers.py   # Tests for helper functions
├── integration/                    # Integration tests (require app setup)
│   └── test_scenario_routes.py    # Tests for API endpoints
└── playwright/                     # E2E tests (require running server)
    ├── pages/
    │   └── scenario_page.py       # Page object for scenario UI
    └── test_scenario_ui.py        # End-to-end UI workflow tests
```

## Running Tests

### Unit Tests (Recommended - Fast & Reliable)

Run all unit tests:
```bash
uv run pytest tests/unit/ -v
```

Run specific test file:
```bash
uv run pytest tests/unit/test_scenario_models.py -v
uv run pytest tests/unit/test_scenario_helpers.py -v
```

**Status:** ✅ All 42 unit tests passing

### Integration Tests

Integration tests require the full application environment to be configured.

```bash
uv run pytest tests/integration/ -v
```

**Note:** These tests may require additional setup (database, config files, etc.) to run successfully.

### E2E Tests (Playwright)

E2E tests require the web server to be running.

1. Start the server in one terminal:
   ```bash
   uv run web/main.py
   ```

2. Run E2E tests in another terminal:
   ```bash
   uv run pytest tests/playwright/test_scenario_ui.py -v
   ```

## Test Coverage

### Unit Tests: `test_scenario_models.py` (25 tests)

**ScenarioValue tests:**
- Creating scenario values with different data types
- Optional labels
- Unique identifiers

**Scenario tests:**
- Creating and managing scenarios
- Adding, updating, and removing values
- Converting to overwrite_input format
- Serialization (to_dict/from_dict)
- Getting values by service

**ScenarioManager tests:**
- Session-based CRUD operations
- Creating and retrieving scenarios
- Listing scenarios by BSN
- Clearing scenarios
- BSN isolation

### Unit Tests: `test_scenario_helpers.py` (17 tests)

**get_evaluation_overrides tests:**
- Scenario mode (only scenarios)
- Claims mode (only claims)
- Scenario mode ignores claims
- Empty scenarios
- Named scenarios
- Filtering by service and law
- Status filtering

**has_active_scenarios tests:**
- Detecting active scenarios
- Named scenarios
- Handling missing request

**get_scenario_summary tests:**
- Summarizing active scenarios
- Grouping values by service
- Metadata inclusion

### Integration Tests: `test_scenario_routes.py` (20+ tests)

**API endpoint tests:**
- `POST /scenarios/value/set` - Setting scenario values
- `GET /scenarios/list` - Listing scenarios
- `GET /scenarios/get` - Getting specific scenario
- `DELETE /scenarios/value/delete` - Deleting values
- `POST /scenarios/clear` - Clearing scenarios
- `GET /scenarios/form` - Getting scenario form
- `GET /scenarios/compare` - Comparing outcomes

**Value parsing tests:**
- Boolean values (true/false variants)
- Number values (int/float)
- Date values
- String values

**Isolation tests:**
- Multiple named scenarios
- BSN isolation

### E2E Tests: `test_scenario_ui.py` (15+ tests)

**UI workflow tests:**
- Toggling scenario mode
- Opening scenario forms
- Submitting scenario values
- Scenario panel visibility
- Clearing scenarios
- Multiple scenario values
- Comparison view
- Persistence across navigation

## Quick Start

To run just the unit tests (fastest, most reliable):

```bash
uv run pytest tests/unit/ -v
```

Expected output:
```
tests/unit/test_scenario_helpers.py::... (17 tests)
tests/unit/test_scenario_models.py::... (25 tests)

====== 42 passed in 2.00s ======
```

## Test Philosophy

- **Unit tests**: Test individual components in isolation, using mocks where needed
- **Integration tests**: Test API endpoints with real FastAPI TestClient
- **E2E tests**: Test complete user workflows in a real browser

## Adding New Tests

When adding new scenario functionality, follow this pattern:

1. **Add unit tests first** - Test the core logic
2. **Add integration tests** - Test API contracts
3. **Add E2E tests** - Test user-facing behavior

Example:
```python
# tests/unit/test_scenario_models.py
def test_new_scenario_feature(self):
    """Test description"""
    scenario = Scenario(name="test", bsn="123")
    # ... test logic
    assert expected_result
```

## Debugging Failures

If tests fail:

1. **Check the error message** - pytest provides detailed traceback
2. **Run with -vv** for more verbose output
3. **Use --tb=short** for shorter tracebacks
4. **Run single test** with `-k test_name`

Example:
```bash
uv run pytest tests/unit/test_scenario_models.py::TestScenario::test_add_value_to_scenario -vv
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Run unit tests
  run: uv run pytest tests/unit/ -v

- name: Run integration tests
  run: uv run pytest tests/integration/ -v

- name: Run E2E tests
  run: |
    uv run web/main.py &
    sleep 5
    uv run pytest tests/playwright/ -v
```
