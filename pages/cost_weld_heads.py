import streamlit as st

from model import load_array_designs, load_materials, load_product
from pages.array_designs import compute_power_for_design


def find_material_by_id(items, mat_id):
    for item in items:
        if str(item.get("id", "")) == str(mat_id):
            return item
    return None


def get_weld_cost_per_weld(weld_item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """
    Cost per weld = (unit_cost / num_welds), converted to GBP if needed.
    """
    if weld_item is None:
        return 0.0

    try:
        currency = (weld_item.get("currency", "USD") or "USD").upper()
        num_welds = float(weld_item.get("num_welds", 0))
    except Exception:
        return 0.0

    if num_welds <= 0:
        return 0.0

    if currency == "USD":
        unit_cost_usd = weld_item.get("unit_cost_usd", None)
        if unit_cost_usd is None:
            return 0.0
        unit_cost_gbp = float(unit_cost_usd) * float(exchange_rate_gbp_per_usd)
    else:
        unit_cost_gbp = float(weld_item.get("unit_cost_gbp", 0))

    return unit_cost_gbp / num_welds


def render():
    st.title("Weld Heads Cost")

    # ---------------------------------------------------------
    # Ensure array design is selected
    # ---------------------------------------------------------
    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the Home page first.")
        return

    selected_name = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # ---------------------------------------------------------
    # Load product, array design, materials
    # ---------------------------------------------------------
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    designs = load_array_designs()
    design = next((d for d in designs if d["name"] == selected_name), None)

    if design is None:
        st.error("Selected array design not found.")
        return

    materials = load_materials()
    weld_items = materials.get("Weld heads", [])

    if not weld_items:
        st.error("No weld head materials found. Add some under Materials → Weld heads.")
        return

    # ---------------------------------------------------------
    # Find weld heads
    # ---------------------------------------------------------
    weld_head_ag = find_material_by_id(weld_items, "Weld_Head_Ag")
    weld_head_al = find_material_by_id(weld_items, "Weld_Head_Al")
    weld_head_au = find_material_by_id(weld_items, "Weld_Head_Au")
    weld_head_bl = find_material_by_id(weld_items, "Weld_Head_BL")

    if weld_head_ag is None:
        st.error("Weld_Head_Ag not found in Weld heads materials.")
        return

    cost_per_weld_ag = get_weld_cost_per_weld(weld_head_ag, exchange_rate)
    cost_per_weld_al = get_weld_cost_per_weld(weld_head_al, exchange_rate)
    cost_per_weld_au = get_weld_cost_per_weld(weld_head_au, exchange_rate)
    cost_per_weld_bl = get_weld_cost_per_weld(weld_head_bl, exchange_rate)

    # ---------------------------------------------------------
    # Compute power (for cost per watt)
    # ---------------------------------------------------------
    power = compute_power_for_design(design)
    array_power = (
        power["P_array_AM15_W"] if illumination == "AM1.5" else power["P_array_AM0_W"]
    )

    # ---------------------------------------------------------
    # WELD COUNTS PER ARRAY
    # ---------------------------------------------------------
    cells = int(design.get("num_cells", 0))
    if cells <= 0:
        st.error("Array design has invalid number of cells.")
        return

    # --- Ag head welds (array welds) ---
    # Top tabs
    top_tabs = 2 * (cells - 1)
    top_tab_welds = top_tabs * 4

    # Negative end
    negative_end_welds = 8

    # Positive end
    positive_end_welds = 4

    # Bypass diode attach welds (module integration, Ag)
    bypass_diode_welds = cells * 2

    ag_welds_per_array = (
        top_tab_welds + negative_end_welds + positive_end_welds + bypass_diode_welds
    )

    # --- Diode weld heads (Al / Au / BL) ---
    # Matches the logic used in cost_summary.py
    bypass_diodes_per_array = cells        # one bypass diode per cell
    blocking_diodes_per_array = 2          # two blocking diodes per array

    al_welds_per_array = bypass_diodes_per_array          # 1 Al weld per bypass diode
    au_welds_per_array = bypass_diodes_per_array          # 1 Au weld per bypass diode
    bl_welds_per_array = 2 * blocking_diodes_per_array    # 2 BL welds per blocking diode (→ 4)

    # Total welds by head (per array)
    total_al_welds = al_welds_per_array
    total_au_welds = au_welds_per_array
    total_bl_welds = bl_welds_per_array
    total_ag_welds = ag_welds_per_array

    total_welds_all_heads = (
        total_al_welds + total_au_welds + total_bl_welds + total_ag_welds
    )

    # ---------------------------------------------------------
    # COST CALCULATION PER ARRAY (by head)
    # ---------------------------------------------------------
    cost_al_per_array = total_al_welds * cost_per_weld_al
    cost_au_per_array = total_au_welds * cost_per_weld_au
    cost_bl_per_array = total_bl_welds * cost_per_weld_bl
    cost_ag_per_array = total_ag_welds * cost_per_weld_ag

    total_cost_all_heads = (
        cost_al_per_array + cost_au_per_array + cost_bl_per_array + cost_ag_per_array
    )

    # ---------------------------------------------------------
    # DISPLAY – LOCATION BREAKDOWN (Ag)
    # ---------------------------------------------------------
    st.subheader("Array weld breakdown (Ag head only)")

    st.write(f"**Top tab welds (Ag):** {top_tab_welds}")
    st.write(f"**Negative end welds (Ag):** {negative_end_welds}")
    st.write(f"**Positive end welds (Ag):** {positive_end_welds}")
    st.write(f"**Bypass diode attach welds (Ag):** {bypass_diode_welds}")

    st.caption(
        "The weld counts above are for the **Ag weld head** only "
        "(tabbing and diode-to-array attachment). "
        "Diode body welds (Al, Au, BL) are shown separately below."
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # DISPLAY – WELDS BY HEAD
    # ---------------------------------------------------------
    st.subheader("Weld counts and cost by head (per array)")

    head_rows = [
        {
            "Head": "Al",
            "Welds per array": total_al_welds,
            "Cost per weld [£]": round(cost_per_weld_al, 6),
            "Cost per array [£]": round(cost_al_per_array, 4),
        },
        {
            "Head": "Au",
            "Welds per array": total_au_welds,
            "Cost per weld [£]": round(cost_per_weld_au, 6),
            "Cost per array [£]": round(cost_au_per_array, 4),
        },
        {
            "Head": "BL",
            "Welds per array": total_bl_welds,
            "Cost per weld [£]": round(cost_per_weld_bl, 6),
            "Cost per array [£]": round(cost_bl_per_array, 4),
        },
        {
            "Head": "Ag",
            "Welds per array": total_ag_welds,
            "Cost per weld [£]": round(cost_per_weld_ag, 6),
            "Cost per array [£]": round(cost_ag_per_array, 4),
        },
    ]

    st.table(head_rows)

    st.markdown("---")

    # ---------------------------------------------------------
    # DISPLAY – TOTALS
    # ---------------------------------------------------------
    st.subheader("Totals")

    st.write(f"**Total Ag welds per array (array welds only):** {total_ag_welds}")
    st.write(f"**Total welds per array (all heads):** {total_welds_all_heads}")

    st.write(
        f"Total weld head cost per array (all heads): "
        f"**£{total_cost_all_heads:.2f}**"
    )
    st.write(
        f"  • of which Ag head contributes: **£{cost_ag_per_array:.2f}**"
    )

    if array_power > 0:
        cost_per_watt_all = total_cost_all_heads / array_power
        st.write(
            f"Cost per watt ({illumination}, all heads): "
            f"**£{cost_per_watt_all:.5f} / W**"
        )
