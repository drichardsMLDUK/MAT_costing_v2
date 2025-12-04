import streamlit as st
import pandas as pd

from labour_model import (
    load_process_steps,
    save_process_steps,
    load_operator_profiles,
    save_operator_profiles,
)


LEVEL_OPTIONS = ["cell", "diode", "array"]
TIMING_BASIS_OPTIONS = ["cell", "diode", "array"]
TIMING_BASIS_LABELS = {
    "cell": "Cell",
    "diode": "Diode",
    "array": "Array (normalised to per cell)",
}

ENTRY_MODES = ["per_unit", "per_batch"]
ENTRY_MODE_LABELS = {
    "per_unit": "Time per unit",
    "per_batch": "Time per batch",
}

TIME_UNITS = ["seconds", "minutes"]


def _safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


def _to_seconds(value: float, unit: str) -> float:
    if unit == "minutes":
        return value * 60.0
    return value


def render():
    st.title("Labour Timing – Standard Times")

    st.markdown(
        """
This page is for defining **standard times**, independent of any array design.

For each process step you can:

- Choose a **Level**: Cell / Diode / Array (for your own organisation).
- Choose a **Timing basis**:
  - **Cell** – you enter a time per cell or per batch of cells.
  - **Diode** – you enter a time per diode or per batch of diodes.
  - **Array** – you enter time for a whole array and the cells/array for that step, which is normalised to time per cell.
- Set a **Yield (%)** to account for scrap/rework.

All times are converted internally to an **effective seconds per cell** or **seconds per diode**, adjusted for yield. You can use these numbers elsewhere in the app for detailed labour costing.
"""
    )

    # -------------------------------------------------------
    # LOAD DATA
    # -------------------------------------------------------
    operator_profiles_dict = load_operator_profiles()
    process_steps = load_process_steps()

    operator_labels = {
        op.id: f"{op.name} (£{op.hourly_rate:.2f}/hr)"
        for op in operator_profiles_dict.values()
    }

    # -------------------------------------------------------
    # OPERATOR PROFILES EDITOR
    # -------------------------------------------------------
    with st.expander("Operator Profiles (edit & save)", expanded=False):

        existing_ops = [
            {
                "id": op.id,
                "name": op.name,
                "job_title": op.job_title,
                "hourly_rate": op.hourly_rate,
            }
            for op in operator_profiles_dict.values()
        ]

        op_df = st.data_editor(
            pd.DataFrame(existing_ops),
            num_rows="dynamic",
            use_container_width=True,
        )

        if st.button("Save Operator Profiles"):
            new_list = op_df.to_dict(orient="records")
            save_operator_profiles(new_list)
            st.success("Saved operator_profiles.yaml ✅")
            _safe_rerun()

    # Reload after potential update
    operator_profiles_dict = load_operator_profiles()
    operator_labels = {
        op.id: f"{op.name} (£{op.hourly_rate:.2f}/hr)"
        for op in operator_profiles_dict.values()
    }

    # -------------------------------------------------------
    # PROCESS STEPS – PER-STEP EXPANDERS
    # -------------------------------------------------------
    st.subheader("Process Steps – Standard Times")

    if not process_steps:
        st.warning(
            "No process steps defined yet in process.yaml. "
            "You can define them directly in the YAML file, then refresh."
        )

    updated_steps = []
    summary_rows = []

    for step in process_steps:
        step_id = step.get("id", "unknown")
        step_name = step.get("name", step_id)

        # Ensure default fields exist for new schema
        level_value = str(step.get("level", "array")).lower()
        if level_value not in LEVEL_OPTIONS:
            level_value = "array"

        basis_value = str(step.get("timing_basis", "array")).lower()
        if basis_value not in TIMING_BASIS_OPTIONS:
            basis_value = "array"

        entry_mode = step.get("timing_entry_mode", "per_unit")
        if entry_mode not in ENTRY_MODES:
            entry_mode = "per_unit"

        time_value = float(step.get("time_value", 0.0))
        time_unit = step.get("time_unit", "seconds")
        if time_unit not in TIME_UNITS:
            time_unit = "seconds"

        batch_units = float(step.get("batch_units", 1.0))
        batch_time_value = float(step.get("batch_time_value", 0.0))
        batch_time_unit = step.get("batch_time_unit", "seconds")
        if batch_time_unit not in TIME_UNITS:
            batch_time_unit = "seconds"

        cells_per_array_for_step = float(step.get("cells_per_array_for_step", 1.0))

        yield_fraction = float(step.get("yield_fraction", 1.0))
        if yield_fraction <= 0:
            yield_fraction = 1.0

        operators_raw = step.get("operators", [])
        if isinstance(operators_raw, int):
            # old schema: just a count
            operators_raw = [{"operator_id": None} for _ in range(operators_raw)]

        with st.expander(f"{step_name}  (`{step_id}`)", expanded=False):

            # ---- Top row: name, level, basis ----
            cols_top = st.columns([2, 1, 1])
            with cols_top[0]:
                name = st.text_input(
                    "Step name",
                    value=step_name,
                    key=f"name_{step_id}",
                )
            with cols_top[1]:
                level_value = st.selectbox(
                    "Level (for organisation)",
                    options=LEVEL_OPTIONS,
                    index=LEVEL_OPTIONS.index(level_value),
                    key=f"level_{step_id}",
                    format_func=lambda x: x.capitalize(),
                )
            with cols_top[2]:
                basis_value = st.selectbox(
                    "Timing basis",
                    options=TIMING_BASIS_OPTIONS,
                    index=TIMING_BASIS_OPTIONS.index(basis_value),
                    key=f"basis_{step_id}",
                    format_func=lambda x: TIMING_BASIS_LABELS.get(x, x),
                )

            # ---- Timing inputs based on basis ----
            raw_time_per_unit_s = 0.0

            if basis_value in ("cell", "diode"):
                # Choose entry mode
                entry_mode = st.selectbox(
                    "Timing entry mode",
                    options=ENTRY_MODES,
                    index=ENTRY_MODES.index(entry_mode),
                    key=f"entry_{step_id}",
                    format_func=lambda x: ENTRY_MODE_LABELS.get(x, x),
                )

                if entry_mode == "per_unit":
                    # Time per cell / per diode
                    col_t = st.columns(2)
                    with col_t[0]:
                        time_value = st.number_input(
                            f"Time per {basis_value}",
                            min_value=0.0,
                            value=time_value,
                            step=0.1,
                            key=f"time_val_{step_id}",
                        )
                    with col_t[1]:
                        time_unit = st.selectbox(
                            "Time unit",
                            options=TIME_UNITS,
                            index=TIME_UNITS.index(time_unit),
                            key=f"time_unit_{step_id}",
                        )
                    raw_time_per_unit_s = _to_seconds(time_value, time_unit)

                else:  # per_batch
                    cols_batch = st.columns(3)
                    label_units = "cells per batch" if basis_value == "cell" else "diodes per batch"
                    with cols_batch[0]:
                        batch_units = st.number_input(
                            label_units,
                            min_value=1.0,
                            value=batch_units if batch_units > 0 else 1.0,
                            step=1.0,
                            key=f"batch_units_{step_id}",
                        )
                    with cols_batch[1]:
                        batch_time_value = st.number_input(
                            "Time per batch",
                            min_value=0.0,
                            value=batch_time_value,
                            step=0.1,
                            key=f"batch_time_val_{step_id}",
                        )
                    with cols_batch[2]:
                        batch_time_unit = st.selectbox(
                            "Batch time unit",
                            options=TIME_UNITS,
                            index=TIME_UNITS.index(batch_time_unit),
                            key=f"batch_time_unit_{step_id}",
                        )

                    if batch_units > 0:
                        raw_time_per_unit_s = _to_seconds(batch_time_value, batch_time_unit) / batch_units
                    else:
                        raw_time_per_unit_s = 0.0

            elif basis_value == "array":
                st.markdown(
                    "This is an **array-level** step that will be normalised to a time per cell."
                )
                cols_arr = st.columns(3)
                with cols_arr[0]:
                    cells_per_array_for_step = st.number_input(
                        "Cells per array (for this step)",
                        min_value=1.0,
                        value=cells_per_array_for_step if cells_per_array_for_step > 0 else 1.0,
                        step=1.0,
                        key=f"cells_array_step_{step_id}",
                    )
                with cols_arr[1]:
                    time_value = st.number_input(
                        "Time per array",
                        min_value=0.0,
                        value=time_value,
                        step=0.1,
                        key=f"time_arr_{step_id}",
                    )
                with cols_arr[2]:
                    time_unit = st.selectbox(
                        "Array time unit",
                        options=TIME_UNITS,
                        index=TIME_UNITS.index(time_unit),
                        key=f"time_unit_arr_{step_id}",
                    )

                if cells_per_array_for_step > 0:
                    raw_time_per_unit_s = _to_seconds(time_value, time_unit) / cells_per_array_for_step
                else:
                    raw_time_per_unit_s = 0.0

            # ---- Yield & operators & notes ----
            cols_mid = st.columns(3)
            with cols_mid[0]:
                yield_percent = st.number_input(
                    "Yield (%)",
                    min_value=1.0,
                    max_value=100.0,
                    value=round(yield_fraction * 100.0, 1),
                    step=1.0,
                    key=f"yield_{step_id}",
                )
                yield_fraction = yield_percent / 100.0
                if yield_fraction <= 0:
                    yield_fraction = 1.0

            with cols_mid[1]:
                existing_ops_ids = [
                    op.get("operator_id")
                    for op in operators_raw
                    if op.get("operator_id") in operator_profiles_dict
                ]
                selected_ops = st.multiselect(
                    "Assigned operators",
                    options=list(operator_labels.keys()),
                    default=existing_ops_ids,
                    format_func=lambda oid: operator_labels.get(oid, oid),
                    key=f"ops_{step_id}",
                )

            with cols_mid[2]:
                notes = st.text_area(
                    "Notes",
                    value=step.get("notes", ""),
                    key=f"notes_{step_id}",
                    height=80,
                )

            # ---- Effective time per unit (after yield) ----
            effective_time_per_unit_s = raw_time_per_unit_s / yield_fraction if yield_fraction > 0 else 0.0

            if basis_value == "cell":
                label_unit = "cell"
            elif basis_value == "diode":
                label_unit = "diode"
            else:
                label_unit = "cell (normalised from array)"

            st.metric(
                f"Effective time per {label_unit}",
                f"{effective_time_per_unit_s:.3f} s",
                help="Includes yield effect; this is the value stored for use elsewhere.",
            )

            # ---- Build updated step dict ----
            new_step = step.copy()
            new_step["name"] = name
            new_step["level"] = level_value
            new_step["timing_basis"] = basis_value
            new_step["timing_entry_mode"] = entry_mode
            new_step["time_value"] = float(time_value)
            new_step["time_unit"] = time_unit
            new_step["batch_units"] = float(batch_units)
            new_step["batch_time_value"] = float(batch_time_value)
            new_step["batch_time_unit"] = batch_time_unit
            new_step["cells_per_array_for_step"] = float(cells_per_array_for_step)
            new_step["yield_fraction"] = float(yield_fraction)
            new_step["time_per_unit_s"] = float(effective_time_per_unit_s)
            new_step["notes"] = notes
            new_step["operators"] = [{"operator_id": oid} for oid in selected_ops]

            updated_steps.append(new_step)

            # For summary table
            summary_rows.append(
                {
                    "Step": name,
                    "Basis": basis_value,
                    "Level": level_value,
                    "Effective time per unit (s)": effective_time_per_unit_s,
                }
            )

    # -------------------------------------------------------
    # SAVE + SUMMARY
    # -------------------------------------------------------
    st.markdown("---")
    st.subheader("Summary & Save")

    if st.button("Save process timings"):
        save_process_steps(updated_steps)
        st.success("Process timings saved to process.yaml ✅")
        _safe_rerun()

    if summary_rows:
        st.markdown("### Effective standard times")
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)
    else:
        st.caption("No steps to summarise yet.")
