"""Scenarios API — serves scenario metadata to the UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "scenarios"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _extract_patient_info(scenario_dir: Path) -> dict[str, Any]:
    """Extract patient information from scenario YAML files."""
    identity = _load_yaml(scenario_dir / "identity_job.yaml")
    opening = _load_yaml(scenario_dir / "opening.yaml")
    symptoms = _load_yaml(scenario_dir / "symptoms.yaml")
    reason = _load_yaml(scenario_dir / "reason_wedding.yaml")
    emotional = _load_yaml(scenario_dir / "emotional_profile.yaml")
    
    # Parse identity content
    identity_content = identity.get("content", "")
    name = "Patient"
    age = 0
    occupation = ""
    
    if "Chloe Harrington" in identity_content:
        name = "Chloe Harrington"
    if "28" in identity_content:
        age = 28
    if "triathlete" in identity_content.lower():
        occupation = "Semi-professional Triathlete"
    
    # Get opening statement
    opening_content = opening.get("content", "").strip().strip('"')
    
    # Get case_id for scenario identification
    case_id = identity.get("case_id", scenario_dir.name)
    
    return {
        "id": scenario_dir.name,
        "case_id": case_id,
        "name": name,
        "age": age,
        "occupation": occupation,
        "gender": "Female" if "chloe" in name.lower() else "Unknown",
        "opening_statement": opening_content,
        "topic": identity.get("topic", ""),
    }


def _build_scenario(scenario_id: str, patient_info: dict) -> dict[str, Any]:
    """Build a complete scenario object for the UI."""
    return {
        "id": scenario_id,
        "groupName": "Amalgam Replacement",
        "title": "Pre-Wedding Aesthetic Consultation",
        "category": "Restorative Dentistry",
        "description": f"Patient {patient_info['name']} wants to replace silver fillings with white ones before their wedding.",
        "patientProfile": {
            "name": patient_info["name"],
            "age": patient_info["age"],
            "gender": patient_info["gender"],
            "occupation": patient_info["occupation"],
            "medicalHistory": "Healthy. No significant medical history.",
        },
        "brief": {
            "scenario": f"{patient_info['name']} is a {patient_info['age']}-year-old {patient_info['occupation'].lower()} who wants all silver (amalgam) fillings replaced with tooth-coloured (composite) fillings before their wedding next month.",
            "task": "Take a history, discuss treatment options, and address the patient's concerns about timing and aesthetics.",
            "instructions": [
                "You cannot examine the patient.",
                "Discuss the pros and cons of amalgam vs composite.",
                "Address any concerns about mercury or longevity.",
                "You have 8 minutes."
            ],
        },
        "goals": [
            "Establish rapport with the patient",
            "Take a focused dental history",
            "Explore the reason for the request",
            "Discuss treatment options clearly",
            "Address aesthetic and timing concerns"
        ],
        "clinicalNotes": "Patient is motivated by upcoming wedding. No symptoms reported."
    }


@router.get("")
async def list_scenarios() -> list[dict[str, Any]]:
    """List all available scenarios."""
    scenarios = []
    
    if not KNOWLEDGE_BASE_DIR.exists():
        return scenarios
    
    for scenario_dir in sorted(KNOWLEDGE_BASE_DIR.iterdir()):
        if scenario_dir.is_dir() and not scenario_dir.name.startswith("."):
            try:
                patient_info = _extract_patient_info(scenario_dir)
                scenario = _build_scenario(scenario_dir.name, patient_info)
                scenarios.append(scenario)
            except Exception as e:
                # Skip malformed scenarios
                continue
    
    return scenarios


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str) -> dict[str, Any]:
    """Get a specific scenario by ID."""
    scenario_dir = KNOWLEDGE_BASE_DIR / scenario_id
    
    if not scenario_dir.exists() or not scenario_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    
    patient_info = _extract_patient_info(scenario_dir)
    return _build_scenario(scenario_id, patient_info)
