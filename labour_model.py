from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import yaml

# ============================================================
# FILE PATHS
# ============================================================
ROOT = Path(__file__).parent
PROCESS_PATH = ROOT / "process.yaml"
OPERATOR_PROFILES_PATH = ROOT / "data" / "operator_profiles.yaml"


# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class OperatorProfile:
    id: str
    name: str
    job_title: str
    hourly_rate: float


@dataclass
class LabourStepResult:
    id: str
    name: str
    timing_basis: str
    quantity_source: str
    units_per_array: float          # logical units (cells, diodes, etc.)
    time_per_unit_s: float          # seconds per unit (or per array if per_array)
    setup_time_s_per_array: float
    total_step_seconds: float
    operator_hours: float
    cost: float
    assigned_operators: List[OperatorProfile]
    notes: str


# ============================================================
# OPERATOR PROFILES LOADING / SAVING
# ============================================================
def load_operator_profiles() -> Dict[str, OperatorProfile]:
    """Load operators from operator_profiles.yaml."""
    if not OPERATOR_PROFILES_PATH.exists():
        return {}

    with open(OPERATOR_PROFILES_PATH, "r") as f:
        raw = yaml.safe_load(f) or {}

    profiles: Dict[str, OperatorProfile] = {}
    for op in raw.get("operators", []):
        profiles[op["id"]] = OperatorProfile(
            id=op["id"],
            name=op.get("name", ""),
            job_title=op.get("job_title", ""),
            hourly_rate=float(op.get("hourly_rate", 0.0)),
        )
    return profiles


def save_operator_profiles(operators_list):
    """Save operator profiles back to YAML."""
    OPERATOR_PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OPERATOR_PROFILES_PATH, "w") as f:
        yaml.safe_dump({"operators": operators_list}, f, sort_keys=False)


# ============================================================
# PROCESS STEPS LOADING / AUTO–CONVERSION
# ============================================================
def load_process_steps() -> List[dict]:
    """Load process steps and auto-upgrade schema (operators, batch/yield/quantity_source)."""
    if not PROCESS_PATH.exists():
        raise FileNotFoundError(f"process.yaml not found at {PROCESS_PATH}")

    with open(PROCESS_PATH, "r") as f:
        raw = yaml.safe_load(f) or {}

    steps: List[dict] = raw.get("process", [])

    upgraded = False

    for step in steps:
        # --- old integer operators → list of slots ---
        ops = step.get("operators")
        if isinstance(ops, int):
            if ops == 0:
                step["operators"] = []
            else:
                step["operators"] = [{"operator_id": None} for _ in range(ops)]
            upgraded = True

        if not isinstance(step.get("operators"), list):
            step["operators"] = []
            upgraded = True

        # Default timing_basis: assume per_array if not set
        if "timing_basis" not in step:
            step["timing_basis"] = "per_array"
            upgraded = True

        # New: quantity_source (what the step scales with)
        if "quantity_source" not in step:
            # Default: array-level step
            step["quantity_source"] = "array"
            upgraded = True

        # New: yield_fraction (for fab/rework steps)
        if "yield_fraction" not in step:
            step["yield_fraction"] = 1.0
            upgraded = True

        # New: input mode hints for UI (doesn't affect calculations)
        if "entry_mode" not in step:
            step["entry_mode"] = "per_unit"  # or "per_batch"
            upgraded = True
        if "batch_units" not in step:
            step["batch_units"] = 1.0
            upgraded = True
        if "batch_seconds" not in step:
            step["batch_seconds"] = 0.0
            upgraded = True

        # Ensure core timing fields exist
        if "time_per_unit_s" not in step:
            step["time_per_unit_s"] = 0.0
            upgraded = True
        if "setup_time_s_per_array" not in step:
            step["setup_time_s_per_array"] = 0.0
            upgraded = True

    if upgraded:
        save_process_steps(steps)

    return steps


def save_process_steps(steps: List[dict]):
    """Write updated process steps back to process.yaml."""
    with open(PROCESS_PATH, "w") as f:
        yaml.safe_dump({"process": steps}, f, sort_keys=False)


# ============================================================
# CALCULATION CORE
# ============================================================
def calculate_labour(
    process_steps: List[dict],
    operator_profiles: Dict[str, OperatorProfile],
    cells_per_string: int,
    strings_per_array: int,
    bypass_diodes_per_array: int = 0,
    blocking_diodes_per_array: int = 0,
):
    """
    Returns:
        {
            "steps": List[LabourStepResult],
            "total_cost": float,
            "total_hours": float,
        }

    Model:

    - timing_basis == "per_array":
        time_per_unit_s is per array, units_per_array = 1

    - timing_basis == "per_unit":
        time_per_unit_s is per unit, units_per_array drawn from quantity_source:
            cells          -> cells_per_array
            strings        -> strings_per_array
            bypass_diodes  -> bypass_diodes_per_array
            blocking_diodes-> blocking_diodes_per_array
            array          -> 1 (degenerate case)
        yield_fraction < 1 means more work per good unit:
            effective_units = units_per_array / yield_fraction
    """

    cells_per_array = cells_per_string * strings_per_array

    qty_map = {
        "array": 1.0,
        "cells": float(cells_per_array),
        "strings": float(strings_per_array),
        "bypass_diodes": float(bypass_diodes_per_array),
        "blocking_diodes": float(blocking_diodes_per_array),
    }

    results: List[LabourStepResult] = []
    total_cost = 0.0
    total_hours = 0.0

    for step in process_steps:
        basis = str(step.get("timing_basis", "per_array")).lower()
        quantity_source = str(step.get("quantity_source", "array"))
        time_per_unit_s = float(step.get("time_per_unit_s", 0.0))
        setup = float(step.get("setup_time_s_per_array", 0.0))
        yield_fraction = float(step.get("yield_fraction", 1.0))
        if yield_fraction <= 0:
            yield_fraction = 1.0  # avoid divide-by-zero; treat as no yield adjustment

        units_per_array = 0.0
        total_seconds = 0.0

        if basis == "per_array":
            units_per_array = 1.0
            total_seconds = time_per_unit_s + setup

        elif basis == "per_unit":
            nominal_units = float(qty_map.get(quantity_source, 0.0))
            effective_units = nominal_units / yield_fraction
            units_per_array = nominal_units
            total_seconds = effective_units * time_per_unit_s + setup

        else:
            # Unknown basis → ignore this step
            units_per_array = 0.0
            total_seconds = 0.0

        operator_hours = total_seconds / 3600.0

        # Resolve assigned operators
        assigned_profiles: List[OperatorProfile] = []
        for op in step.get("operators", []):
            oid = op.get("operator_id")
            if oid and oid in operator_profiles:
                assigned_profiles.append(operator_profiles[oid])

        step_cost = sum(op.hourly_rate * operator_hours for op in assigned_profiles)

        total_cost += step_cost
        total_hours += operator_hours

        results.append(
            LabourStepResult(
                id=step.get("id", ""),
                name=step.get("name", ""),
                timing_basis=basis,
                quantity_source=quantity_source,
                units_per_array=units_per_array,
                time_per_unit_s=time_per_unit_s,
                setup_time_s_per_array=setup,
                total_step_seconds=total_seconds,
                operator_hours=operator_hours,
                cost=step_cost,
                assigned_operators=assigned_profiles,
                notes=step.get("notes", ""),
            )
        )

    return {
        "steps": results,
        "total_cost": total_cost,
        "total_hours": total_hours,
    }
