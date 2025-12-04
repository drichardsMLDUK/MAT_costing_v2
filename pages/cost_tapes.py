import streamlit as st

from model import load_array_designs, load_materials, load_product
from pages.array_designs import compute_power_for_design


# ============================================================
# Helper function
# ============================================================

def get_tape_cost_per_m(item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """
    Compute tape cost per meter (GBP). Supports your YAML fields.
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

    if roll_cost_gbp is not None:
        try:
            return float(roll_cost_gbp) / roll_length_m
        except:
            return 0.0

    if roll_cost_usd is not None:
        try:
            return float(roll_cost_usd) * exchange_rate_gbp_per_usd / roll_length_m
        except:
            return 0.0

    return 0.0


# ============================================================
# Main Render
# ============================================================

def render():
    st.title("Tapes Cost")

    # Require array selection
    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the Home page first.")
        return

    selected = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # Load core data
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    designs = load_array_designs()
    design = next((d for d in designs if d["name"] == selected), None)

    if design is None:
        st.error("Selected array design not found.")
        return

    materials = load_materials()
    tape_items = materials.get("Tapes", [])

    if not tape_items:
        st.error("No tape materials found. Add some under Materials → Tapes.")
        return

    # Compute array power
    power = compute_power_for_design(design)
    array_power = power["P_array_AM15_W"] if illumination == "AM1.5" else power["P_array_AM0_W"]

    # ============================================================
    # Compute geometry
    # ============================================================

    num_cells = float(design["num_cells"])
    cell_h = float(design["cell_height_mm"])
    gap = float(design["gap_between_cells_mm"])
    pos_gap = float(design["positive_end_gap_mm"])
    neg_gap = float(design["negative_end_gap_mm"])

    base_length_mm = (
        cell_h * num_cells
        + gap * max(num_cells - 1, 0)
        + pos_gap
        + neg_gap
    )

    perimeter_length_mm = 2 * base_length_mm + 140.0
    perimeter_length_m = perimeter_length_mm / 1000.0

    st.subheader("Tape Geometry")
    st.markdown(
        f"""
        **Base length calculation:**  
        Cell height × cells = {cell_h:.3f} × {num_cells:.0f}  
        Gaps = {gap:.3f} × {max(num_cells-1, 0):.0f}  
        End gaps = +{pos_gap:.3f} mm, +{neg_gap:.3f} mm  

        **Base length:** {base_length_mm:.2f} mm  
        **Perimeter taping length:** {perimeter_length_mm:.2f} mm  
        **Perimeter length (m):** {perimeter_length_m:.2f} m
        """
    )

    st.markdown("---")

    # ============================================================
    # Initialise persistent session state
    # ============================================================

    if "cost_tapes_state" not in st.session_state:
        st.session_state["cost_tapes_state"] = {
            "perimeter_tape_idx": 0,
            "other_tape_idx": 0,
            "other_length_mm": 0.0,
        }

    state = st.session_state["cost_tapes_state"]

    # Build labels
    labels = [
        f"{i}: {t.get('id','(no id)')} – {t.get('name','(no name)')}"
        for i, t in enumerate(tape_items)
    ]

    # ============================================================
    # PERIMETER TAPING
    # ============================================================

    st.subheader("Perimeter Taping")

    current_perim_idx = min(state["perimeter_tape_idx"], len(labels) - 1)

    perim_sel = st.selectbox(
        "Perimeter tape material",
        labels,
        index=current_perim_idx,
        key="cost_tapes_perimeter_select",
    )
    perim_idx = int(perim_sel.split(":", 1)[0])
    state["perimeter_tape_idx"] = perim_idx

    perim_item = tape_items[perim_idx]
    cost_per_m_perim = get_tape_cost_per_m(perim_item, exchange_rate)
    cost_perimeter = cost_per_m_perim * perimeter_length_m

    st.markdown(
        f"""
        **Cost per meter:** £{cost_per_m_perim:.2f}  
        **Perimeter length:** {perimeter_length_m:.2f} m  
        **Perimeter taping cost:** £{cost_perimeter:.2f}
        """
    )

    st.markdown("---")

    # ============================================================
    # OTHER TAPING
    # ============================================================

    st.subheader("Other Taping")

    current_other_idx = min(state["other_tape_idx"], len(labels) - 1)

    other_sel = st.selectbox(
        "Other tape material",
        labels,
        index=current_other_idx,
        key="cost_tapes_other_select",
    )
    other_idx = int(other_sel.split(":", 1)[0])
    state["other_tape_idx"] = other_idx

    other_item = tape_items[other_idx]

    other_length_mm = st.number_input(
        "Other taping length (mm)",
        min_value=0.0,
        step=10.0,
        key="cost_tapes_other_length",
        value=float(state["other_length_mm"]),
    )
    state["other_length_mm"] = other_length_mm

    other_length_m = other_length_mm / 1000.0
    cost_per_m_other = get_tape_cost_per_m(other_item, exchange_rate)
    cost_other = cost_per_m_other * other_length_m

    st.markdown(
        f"""
        **Cost per meter:** £{cost_per_m_other:.2f}  
        **Other taping length:** {other_length_m:.2f} m  
        **Other taping cost:** £{cost_other:.2f}
        """
    )

    st.markdown("---")

    # ============================================================
    # TOTAL
    # ============================================================

    total_tape_cost = cost_perimeter + cost_other

    st.subheader("Total Tape Cost")
    st.write(f"**Total tape cost:** £{total_tape_cost:.2f}")

    if array_power > 0:
        st.write(
            f"**Cost per watt ({illumination}):** "
            f"£{(total_tape_cost / array_power):.2f} per W"
        )
