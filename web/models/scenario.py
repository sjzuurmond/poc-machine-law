"""
Data models for what-if scenarios.

Scenarios allow users to temporarily override values for calculations
without creating persistent claims in the database.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ScenarioValue:
    """A single scenario override value"""

    service: str
    law: str
    key: str
    value: Any
    label: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "service": self.service,
            "law": self.law,
            "key": self.key,
            "value": self.value,
            "label": self.label,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioValue":
        """Create from dictionary"""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            service=data["service"],
            law=data["law"],
            key=data["key"],
            value=data["value"],
            label=data.get("label"),
            timestamp=timestamp or datetime.now(),
        )


@dataclass
class Scenario:
    """A collection of scenario values with metadata"""

    name: str
    bsn: str
    values: dict[str, ScenarioValue] = field(default_factory=dict)
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_value(self, value: ScenarioValue) -> None:
        """Add or update a scenario value"""
        key = self._make_key(value.service, value.law, value.key)
        self.values[key] = value
        self.updated_at = datetime.now()

    def remove_value(self, service: str, law: str, key: str) -> bool:
        """Remove a scenario value, returns True if found and removed"""
        scenario_key = self._make_key(service, law, key)
        if scenario_key in self.values:
            del self.values[scenario_key]
            self.updated_at = datetime.now()
            return True
        return False

    def get_value(self, service: str, law: str, key: str) -> ScenarioValue | None:
        """Get a specific scenario value"""
        scenario_key = self._make_key(service, law, key)
        return self.values.get(scenario_key)

    def get_values_for_service(self, service: str) -> list[ScenarioValue]:
        """Get all scenario values for a specific service"""
        return [v for v in self.values.values() if v.service == service]

    def get_overwrite_input(self) -> dict[str, dict[str, Any]]:
        """
        Convert scenario values to overwrite_input format for engine.
        Returns: {service: {key: value}}
        """
        overwrite_input = {}
        for scenario_value in self.values.values():
            service = scenario_value.service
            if service not in overwrite_input:
                overwrite_input[service] = {}
            overwrite_input[service][scenario_value.key] = scenario_value.value
        return overwrite_input

    def clear(self) -> None:
        """Clear all scenario values"""
        self.values = {}
        self.updated_at = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "bsn": self.bsn,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "values": {k: v.to_dict() for k, v in self.values.items()},
            "value_count": len(self.values),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        """Create from dictionary"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        values = {}
        for key, value_data in data.get("values", {}).items():
            values[key] = ScenarioValue.from_dict(value_data)

        return cls(
            name=data["name"],
            bsn=data["bsn"],
            description=data.get("description", ""),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            values=values,
        )

    @staticmethod
    def _make_key(service: str, law: str, key: str) -> str:
        """Create a unique key for a scenario value"""
        return f"{service}:{law}:{key}"


class ScenarioManager:
    """Manages scenarios in session storage"""

    SESSION_KEY = "scenarios"

    @staticmethod
    def get_or_create(session: dict, bsn: str, name: str = "default") -> Scenario:
        """Get or create a scenario from session"""
        session_key = f"{ScenarioManager.SESSION_KEY}:{bsn}:{name}"

        if session_key in session:
            return Scenario.from_dict(session[session_key])

        scenario = Scenario(name=name, bsn=bsn)
        session[session_key] = scenario.to_dict()
        return scenario

    @staticmethod
    def save(session: dict, scenario: Scenario) -> None:
        """Save scenario to session"""
        session_key = f"{ScenarioManager.SESSION_KEY}:{scenario.bsn}:{scenario.name}"
        session[session_key] = scenario.to_dict()

    @staticmethod
    def delete(session: dict, bsn: str, name: str) -> bool:
        """Delete a scenario from session"""
        session_key = f"{ScenarioManager.SESSION_KEY}:{bsn}:{name}"
        if session_key in session:
            del session[session_key]
            return True
        return False

    @staticmethod
    def list_scenarios(session: dict, bsn: str) -> list[dict[str, Any]]:
        """List all scenarios for a BSN"""
        prefix = f"{ScenarioManager.SESSION_KEY}:{bsn}:"
        scenarios = []

        for key, value in session.items():
            if key.startswith(prefix):
                scenarios.append(value)

        return scenarios

    @staticmethod
    def clear_all(session: dict, bsn: str) -> int:
        """Clear all scenarios for a BSN, returns count of deleted scenarios"""
        prefix = f"{ScenarioManager.SESSION_KEY}:{bsn}:"
        keys_to_delete = [key for key in session.keys() if key.startswith(prefix)]

        for key in keys_to_delete:
            del session[key]

        return len(keys_to_delete)
