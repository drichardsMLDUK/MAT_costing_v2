import streamlit as st

from model import load_array_designs, load_materials, load_product
from pages.array_designs import compute_power_for_design


# ============================================================
# Helper functions
# ============================================================

def get_kapton_cost_per_disk(item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """Return Kapton insulation cost per disk in GBP."""
    # If already precomputed
    if "cost_per_disk_gbp" in item:
        try:
            return float(item["cost_per_disk_gbp"])
        except (TypeError, ValueError):
            pass

    disks = item.get("disks_per_roll", None)
    if not disks:
        return 0.0

    try:
        disks = float(disks)
    except (TypeError, ValueError):
        return 0.0

    if disks <= 0:
        return 0.0

    total_cost_gbp = item.get("total_cost_gbp", None)
    if total_cost_gbp is not None:
        try:
            return float(total_cost_gbp) / disks
        except (TypeError, ValueError):
            return 0.0

    roll_cost_usd = item.get("roll_cost_usd", None)
    currency = (item.get("currency", "USD") or "USD").upper()

    if roll_cost_usd is not None and currency == "USD":
        try:
            total_cost_gbp = float(roll_cost_usd) * float(exchange_rate_gbp_per_usd)
            return total_cost_gbp / disks
        except (TypeError, ValueError):
            return 0.0

    return 0.0


def get_epoxy_cost_per_ml(item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """Return epoxy cost per mL in GBP."""
    if "cost_per_ml_gbp" in item:
        try:
            return float(item["cost_per_ml_gbp"])
        except (TypeError, ValueError):
            pass

    volume_ml = item.get("volume_ml", None)
    if not volume_ml:
        return 0.0

    try:
        volume_ml = float(volume_ml)
    except (TypeError, ValueError):
        return 0.0

    if volume_ml <= 0:
        return 0.0

    total_cost_gbp = item.get("total_cost_gbp", None)
    if total_cost_gbp is not None:
        try:
            return float(total_cost_gbp) / volume_ml
        except (TypeError, ValueError):
            return 0.0

    total_cost_usd = item.get("total_cost_usd", None)
    currency = (item.get("currency", "GBP") or "GBP").upper()

    if total_cost_usd is not None and currency == "USD":
        try:
            total_cost_gbp = float(total_cost_usd) * float(exchange_rate_gbp_per_usd)
            return total_cost_gbp / volume_ml
        except (TypeError, ValueError):
            return 0.0

    return 0.0


# ============================================================
# Main render
# ============================================================

def render():
    st.title("Misc Cost (Kapton & Epoxy)")

    # ------------------------------------------------------------------
    # Ensure array design selected
    # ------------------------------------------------------------------
    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the Home page first.")
        return

    selected_name = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # Load core data
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    designs = load_array_designs()
    design = next((d for d in designs if d["name"] == selected_name), None)

    if design is None:
        st.error("Selected array design not found.")
        return

    materials = load_materials()
    misc_items = materials.get("Misc", [])

    if not misc_items:
        st.error("No Misc materials found. Add Kapton and Epoxy in Materials → Misc.")
        return

    # Power
    power = compute_power_for_design(design)
    array_power = (
        power["P_array_AM15_W"]
        if illumination == "AM1.5"
        else power["P_array_AM0_W"]
    )

    num_cells = int(design.get("num_cells", 0))
    if num_cells <= 0:
        st.error("Array design has invalid number of cells.")
        return

    # ------------------------------------------------------------------
    # Initialise persistent state (only once)
    # ------------------------------------------------------------------
    if "cost_misc_state" not in st.session_state:
        st.session_state["cost_misc_state"] = {
            "epoxy_index": 0,
            "epoxy_per_diode_ml": 0.0,
        }

    state = st.session_state["cost_misc_state"]

    # ------------------------------------------------------------------
    # KAPTON INSULATION
    # ------------------------------------------------------------------
    st.subheader("Kapton Insulation Tabs")

    kapton_item = None
    for it in misc_items:
        if str(it.get("id", "")) == "Kapton_Insulation" or str(it.get("type", "")).lower() == "kapton":
            kapton_item = it
            break

    if kapton_item is None:
        st.error(
            "Kapton insulation material not found in Misc. "
            "Expected id 'Kapton_Insulation' or type 'Kapton'."
        )
        kapton_cost_total = 0.0
    else:
        disks_per_array = num_cells  # one disk per bypass diode
        cost_per_disk = get_kapton_cost_per_disk(kapton_item, exchange_rate)
        kapton_cost_total = cost_per_disk * disks_per_array

        st.write(
            f"- Kapton material: **{kapton_item.get('name','(no name)')}** "
            f"(id: {kapton_item.get('id','')})"
        )
        st.write(f"- Number of disks (same as bypass diodes): **{disks_per_array}**")
        st.write(f"- Cost per disk: **£{cost_per_disk:.2f}**")
        st.write(f"→ **Kapton cost:** £{kapton_cost_total:.2f}")

    st.markdown("---")

    # ------------------------------------------------------------------
    # EPOXY
    # ------------------------------------------------------------------
    st.subheader("Epoxy")

    epoxy_items = [it for it in misc_items if str(it.get("type", "")).lower() == "epoxy"]

    if not epoxy_items:
        st.error("No epoxy items found in Misc (type 'Epoxy').")
        epoxy_total_cost = 0.0
    else:
        epoxy_labels = [
            f"{i}: {it.get('id','(no id)')} – {it.get('name','(no name)')}"
            for i, it in enumerate(epoxy_items)
        ]

        # Ensure index is in range
        current_epoxy_idx = min(state["epoxy_index"], len(epoxy_labels) - 1)

        epoxy_sel = st.selectbox(
            "Select epoxy type",
            epoxy_labels,
            index=current_epoxy_idx,
            key="cost_misc_epoxy_select",
        )
        epoxy_idx = int(epoxy_sel.split(":", 1)[0])
        state["epoxy_index"] = epoxy_idx
        epoxy_item = epoxy_items[epoxy_idx]

        st.write("Enter the amount of epoxy used **per diode** (mL).")

        amount_per_diode_ml = st.number_input(
            "Epoxy usage per diode (mL)",
            min_value=0.0,
            step=0.01,
            key="cost_misc_epoxy_per_diode",
            value=float(state["epoxy_per_diode_ml"]),
        )
        state["epoxy_per_diode_ml"] = amount_per_diode_ml

        num_diodes_for_epoxy = 2  # as per your description
        total_epoxy_ml = amount_per_diode_ml * num_diodes_for_epoxy

        cost_per_ml = get_epoxy_cost_per_ml(epoxy_item, exchange_rate)
        epoxy_total_cost = cost_per_ml * total_epoxy_ml

        st.write(
            f"- Epoxy selected: **{epoxy_item.get('name','(no name)')}** "
            f"(id: {epoxy_item.get('id','')})"
        )
        st.write(f"- Amount per diode: **{amount_per_diode_ml:.2f} mL**")
        st.write(f"- Number of diodes (for epoxy): **{num_diodes_for_epoxy}**")
        st.write(f"- Total epoxy used: **{total_epoxy_ml:.2f} mL**")
        st.write(f"- Cost per mL: **£{cost_per_ml:.2f}**")
        st.write(f"→ **Epoxy cost:** £{epoxy_total_cost:.2f}")

    st.markdown("---")

    # ------------------------------------------------------------------
    # TOTAL MISC COST
    # ------------------------------------------------------------------
    st.subheader("Total Misc Cost")

    total_misc_cost = kapton_cost_total + epoxy_total_cost

    st.write(f"**Kapton cost:** £{kapton_cost_total:.2f}")
    st.write(f"**Epoxy cost:** £{epoxy_total_cost:.2f}")
    st.write(f"**Total Misc cost:** £{total_misc_cost:.2f}")

    if array_power > 0:
        st.write(
            f"**Cost per watt ({illumination}):** "
            f"£{(total_misc_cost / array_power):.2f} / W"
        )
