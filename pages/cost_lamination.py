import streamlit as st

from model import load_array_designs, load_materials, load_product
from pages.array_designs import compute_power_for_design


# ============================================================
# Helper Functions
# ============================================================

def get_lamination_cost_per_m(item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """
    Compute lamination cost per meter (GBP).

    Supports your YAML fields:
    - roll_length_value
    - roll_length_unit ('m' or 'ft')
    - roll_cost_gbp (preferred)
    - roll_cost_usd (optional)
    - roll_currency
    """
    try:
        length_value = float(item.get("roll_length_value", 0.0))
        length_unit = (item.get("roll_length_unit", "m") or "m").lower()
    except Exception:
        return 0.0

    if length_value <= 0:
        return 0.0

    # Convert ft → m
    if length_unit in ("ft", "foot", "feet"):
        roll_length_m = length_value * 0.3048
    else:
        roll_length_m = length_value

    roll_cost_gbp = item.get("roll_cost_gbp", None)
    roll_cost_usd = item.get("roll_cost_usd", None)

    # Preferred: direct GBP roll cost
    if roll_cost_gbp is not None:
        try:
            return float(roll_cost_gbp) / roll_length_m
        except Exception:
            return 0.0

    # Fallback: USD roll cost
    if roll_cost_usd is not None:
        try:
            return float(roll_cost_usd) * exchange_rate_gbp_per_usd / roll_length_m
        except Exception:
            return 0.0

    return 0.0


# ============================================================
# Main Render
# ============================================================

def render():
    st.title("Lamination Cost")

    # ---------------------------------------------------------
    # Ensure array design is selected
    # ---------------------------------------------------------
    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the **Home** page first.")
        return

    selected_name = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # ---------------------------------------------------------
    # Load product, designs, materials
    # ---------------------------------------------------------
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    designs = load_array_designs()
    design = next((d for d in designs if d["name"] == selected_name), None)

    if design is None:
        st.error("Selected array design not found.")
        return

    materials = load_materials()
    lam_items = materials.get("Lamination", [])

    if not lam_items:
        st.error("No lamination materials found. Add some under Materials → Lamination.")
        return

    # ---------------------------------------------------------
    # Compute array power (for cost per W)
    # ---------------------------------------------------------
    power = compute_power_for_design(design)
    array_power = (
        power["P_array_AM15_W"]
        if illumination == "AM1.5"
        else power["P_array_AM0_W"]
    )

    # ---------------------------------------------------------
    # Compute base lamination length
    # ---------------------------------------------------------
    num_cells = float(design.get("num_cells", 0))
    cell_h = float(design.get("cell_height_mm", 0.0))
    gap = float(design.get("gap_between_cells_mm", 0.0))
    pos_gap = float(design.get("positive_end_gap_mm", 0.0))
    neg_gap = float(design.get("negative_end_gap_mm", 0.0))

    if num_cells <= 0:
        st.error("Array design has invalid number of cells.")
        return

    base_length_mm = (
        cell_h * num_cells
        + gap * max(num_cells - 1, 0)
        + pos_gap
        + neg_gap
    )
    base_length_m = base_length_mm / 1000.0

    st.subheader("Base Lamination Length")
    st.write(
        f"""
        Calculated from array design:

        - Cell height: **{cell_h:.3f} mm**  
        - Number of cells: **{num_cells:.0f}**  
        - Gap between cells: **{gap:.3f} mm**  
        - Positive end gap: **{pos_gap:.3f} mm**  
        - Negative end gap: **{neg_gap:.3f} mm**  

        **Base length:** {base_length_mm:.2f} mm ({base_length_m:.2f} m)
        """
    )
    st.markdown("---")

    # ---------------------------------------------------------
    # Initialise persistent state (only once)
    # ---------------------------------------------------------
    if "cost_lamination_state" not in st.session_state:
        # Defaults: first 3 materials for layers, first material for liner, 0 waste
        st.session_state["cost_lamination_state"] = {
            "layer_indices": [0, 0, 0],
            "layer_waste_mm": [0.0, 0.0, 0.0],
            "liner_index": 0,
        }

    state = st.session_state["cost_lamination_state"]

    # Label list for selects
    lam_labels = [
        f"{i}: {it.get('id','(no id)')} – {it.get('name','(no name)')}"
        for i, it in enumerate(lam_items)
    ]

    # ============================================================
    # Lamination Stack – 3 layers
    # ============================================================
    st.subheader("Lamination Stack (3 Layers)")

    total_stack_cost = 0.0
    total_stack_length_m = 0.0

    for layer_idx in range(3):
        st.markdown(f"### Layer {layer_idx + 1}")

        # Ensure index is in range
        current_index = state["layer_indices"][layer_idx]
        if current_index >= len(lam_labels):
            current_index = 0
            state["layer_indices"][layer_idx] = 0

        sel = st.selectbox(
            f"Material for Layer {layer_idx + 1}",
            lam_labels,
            index=current_index,
            key=f"cost_lamination_layer_{layer_idx}_material",
        )
        sel_idx = int(sel.split(":", 1)[0])
        state["layer_indices"][layer_idx] = sel_idx
        layer_item = lam_items[sel_idx]

        col_len = st.columns(3)
        with col_len[0]:
            st.write(f"Base required: **{base_length_mm:.2f} mm**")

        # Waste per layer (mm)
        default_waste = float(state["layer_waste_mm"][layer_idx])
        with col_len[1]:
            waste_mm = st.number_input(
                f"Waste for Layer {layer_idx + 1} (mm)",
                min_value=0.0,
                step=1.0,
                value=default_waste,
                key=f"cost_lamination_layer_{layer_idx}_waste",
            )
        state["layer_waste_mm"][layer_idx] = waste_mm

        total_length_mm = base_length_mm + waste_mm
        total_length_m = total_length_mm / 1000.0

        with col_len[2]:
            waste_pct = (waste_mm / total_length_mm * 100.0) if total_length_mm > 0 else 0.0
            st.write(f"Waste: **{waste_pct:.2f}%**")

        cost_per_m = get_lamination_cost_per_m(layer_item, exchange_rate)
        cost_layer = cost_per_m * total_length_m

        st.write(
            f"Cost per meter: **£{cost_per_m:.2f}**, "
            f"Length: **{total_length_m:.2f} m** → "
            f"Layer cost: **£{cost_layer:.2f}**"
        )

        total_stack_cost += cost_layer
        total_stack_length_m += total_length_m

        st.markdown("---")

    # ============================================================
    # Welding Liner
    # ============================================================
    st.subheader("Welding Liner")

    # Ensure liner index in range
    liner_index = state["liner_index"]
    if liner_index >= len(lam_labels):
        liner_index = 0
        state["liner_index"] = 0

    liner_sel = st.selectbox(
        "Select welding liner material",
        lam_labels,
        index=liner_index,
        key="cost_lamination_liner_material",
    )
    liner_idx = int(liner_sel.split(":", 1)[0])
    state["liner_index"] = liner_idx
    liner_item = lam_items[liner_idx]

    liner_length_m = base_length_m
    liner_cost_per_m = get_lamination_cost_per_m(liner_item, exchange_rate)
    liner_cost = liner_cost_per_m * liner_length_m

    st.write(
        f"Base length: **{base_length_mm:.2f} mm** ({liner_length_m:.2f} m)  |  "
        f"Cost per m: **£{liner_cost_per_m:.2f}**  →  "
        f"Liner cost: **£{liner_cost:.2f}**"
    )

    # ============================================================
    # TOTALS
    # ============================================================
    st.markdown("---")
    st.subheader("Total Lamination Cost")

    total_lam_cost = total_stack_cost + liner_cost
    total_lam_length_m = total_stack_length_m + liner_length_m

    st.write(f"**Total lamination length (layers + liner):** {total_lam_length_m:.2f} m")
    st.write(f"**Total lamination cost:** £{total_lam_cost:.2f}")

    if array_power > 0:
        st.write(
            f"**Cost per watt ({illumination}):** "
            f"£{(total_lam_cost / array_power):.2f} / W"
        )
