import streamlit as st

from model import (
    load_materials,
    load_array_designs,
    load_product,
    MaterialItem,
)
from pages.array_designs import compute_power_for_design


# ------------------------ HELPERS ------------------------


def get_silver_cost_per_mm(
    silver_item: MaterialItem,
    exchange_rate_gbp_per_usd: float,
    override_width_mm: float | None = None,
) -> float:
    """
    Compute cost per mm of silver in GBP from geometry & price.

    If override_width_mm is provided, that width is used instead of the
    width stored in the silver item (useful for diode tabs with custom width).
    """
    try:
        price_per_g = float(silver_item.get("price_per_g", 0))
        currency = (silver_item.get("price_currency", "USD") or "USD").upper()
        width_mm = float(
            override_width_mm
            if override_width_mm is not None
            else silver_item.get("width_mm", 0)
        )
        thickness_mm = float(silver_item.get("thickness_mm", 0))
        density_g_cm3 = float(silver_item.get("density_g_cm3", 0))
    except Exception:
        return 0.0

    if width_mm <= 0 or thickness_mm <= 0 or density_g_cm3 <= 0:
        return 0.0

    # Convert price to GBP
    if currency == "USD":
        price_per_g_gbp = price_per_g * float(exchange_rate_gbp_per_usd)
    else:
        price_per_g_gbp = price_per_g

    # Geometry conversion:
    # width_mm -> cm, thickness_mm -> cm, length = 1 mm -> 0.1 cm
    width_cm = width_mm / 10.0
    thickness_cm = thickness_mm / 10.0
    length_cm = 0.1  # 1 mm

    volume_cm3_per_mm = width_cm * thickness_cm * length_cm
    grams_per_mm = volume_cm3_per_mm * density_g_cm3

    return grams_per_mm * price_per_g_gbp


def get_diode_price_gbp(diode_item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """Return diode price in GBP (unit price) from materials entry."""
    currency = (diode_item.get("currency", "USD") or "USD").upper()

    try:
        if currency == "USD":
            unit_cost_usd = diode_item.get("unit_cost_usd", None)
            if unit_cost_usd is None:
                return 0.0
            return float(unit_cost_usd) * float(exchange_rate_gbp_per_usd)
        else:
            unit_cost_gbp = diode_item.get("unit_cost_gbp", None)
            if unit_cost_gbp is None:
                return 0.0
            return float(unit_cost_gbp)
    except (TypeError, ValueError):
        return 0.0


def get_weld_cost_per_weld(
    weld_item: dict, exchange_rate_gbp_per_usd: float
) -> float:
    """
    Compute cost per weld in GBP for a weld head.

    unit_cost / num_welds
    """
    currency = (weld_item.get("currency", "USD") or "USD").upper()
    try:
        num_welds = float(weld_item.get("num_welds", 0))
    except (TypeError, ValueError):
        return 0.0

    if num_welds <= 0:
        return 0.0

    try:
        if currency == "USD":
            unit_cost_usd = weld_item.get("unit_cost_usd", None)
            if unit_cost_usd is None:
                return 0.0
            total_cost_gbp = float(unit_cost_usd) * float(exchange_rate_gbp_per_usd)
        else:
            unit_cost_gbp = weld_item.get("unit_cost_gbp", None)
            if unit_cost_gbp is None:
                return 0.0
            total_cost_gbp = float(unit_cost_gbp)
    except (TypeError, ValueError):
        return 0.0

    return total_cost_gbp / num_welds


def find_material_by_id(items: list[dict], mat_id: str | None) -> dict | None:
    if not mat_id:
        return None
    for item in items:
        if str(item.get("id", "")) == str(mat_id):
            return item
    return None


# ------------------------ MAIN RENDER ------------------------


def render():
    st.title("Diodes Cost")

    # ---------------------------------------------------------
    # Ensure array design selected
    # ---------------------------------------------------------
    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the **Home** page first.")
        return

    selected_name = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # Load product (for exchange rate)
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    # Load designs
    designs = load_array_designs()
    design = next((d for d in designs if d["name"] == selected_name), None)

    if design is None:
        st.error("Selected array design not found. Please re-select on Home page.")
        return

    # Power
    power = compute_power_for_design(design)
    array_power = power["P_array_AM15_W"] if illumination == "AM1.5" else power["P_array_AM0_W"]

    # Cell count
    num_cells = int(design.get("num_cells", 0))
    if num_cells <= 0:
        st.error("Array design has invalid number of cells.")
        return

    # ---------------------------------------------------------
    # Load materials
    # ---------------------------------------------------------
    materials = load_materials()
    diode_items = materials.get("Diodes", [])
    silver_items = materials.get("Silver Ribbon", [])
    weld_items = materials.get("Weld heads", [])

    if not diode_items:
        st.error("No diode materials found. Add some under Materials → Diodes.")
        return

    if not silver_items:
        st.error("No silver ribbon materials found. Add some under Materials → Silver Ribbon.")
        return

    if not weld_items:
        st.error("No weld head materials found. Add some under Materials → Weld heads.")
        return

    # Weld heads we need
    weld_head_al = find_material_by_id(weld_items, "Weld_Head_Al")
    weld_head_au = find_material_by_id(weld_items, "Weld_Head_Au")
    weld_head_bl = find_material_by_id(weld_items, "Weld_Head_BL")

    if weld_head_al is None or weld_head_au is None or weld_head_bl is None:
        st.error(
            "One or more required weld heads (Weld_Head_Al, Weld_Head_Au, Weld_Head_BL) "
            "are missing from Materials → Weld heads."
        )
        return

    cost_per_weld_al = get_weld_cost_per_weld(weld_head_al, exchange_rate)
    cost_per_weld_au = get_weld_cost_per_weld(weld_head_au, exchange_rate)
    cost_per_weld_bl = get_weld_cost_per_weld(weld_head_bl, exchange_rate)

    # ---------------------------------------------------------
    # Initialise defaults in session_state (only once)
    # ---------------------------------------------------------
    if "cost_diodes_state" not in st.session_state:
        st.session_state["cost_diodes_state"] = {
            "bypass_diode_index": 0,
            "bypass_silver_index": 0,
            "bypass_tab_length_mm": 5.0,
            "bypass_tab_width_mm": 1.5,
            "bypass_yield_percent": 80,
            "blocking_diode_index": 0,
            "blocking_yield_percent": 90,
        }

    state = st.session_state["cost_diodes_state"]

    # Shared labels
    diode_labels = [
        f"{i}: {d.get('id', '(no id)')} – {d.get('name', '(no name)')}"
        for i, d in enumerate(diode_items)
    ]
    silver_labels = [
        f"{i}: {s.get('id', '(no id)')} – {s.get('name', '(no name)')} "
        f"({s.get('width_mm', '?')} mm)"
        for i, s in enumerate(silver_items)
    ]

    # ---------------------------------------------------------
    # BYPASS DIODES
    # ---------------------------------------------------------
    st.subheader("Bypass Diodes")

    st.markdown(
        f"""
        - One bypass diode per **cell** → **{num_cells} bypass diodes**  
        - Two silver tabs per diode (each welded with Al and Au weld heads)  
        - Process yield default ~80% (configurable)
        """
    )

    bypass_choice = st.selectbox(
        "Bypass diode material",
        diode_labels,
        index=min(state["bypass_diode_index"], len(diode_labels) - 1),
        key="cost_diodes_bypass_diode",
    )
    bypass_idx = int(bypass_choice.split(":", 1)[0])
    state["bypass_diode_index"] = bypass_idx
    bypass_diode_item = diode_items[bypass_idx]
    price_bypass_gbp = get_diode_price_gbp(bypass_diode_item, exchange_rate)

    bypass_silver_choice = st.selectbox(
        "Silver material for bypass diode tabs",
        silver_labels,
        index=min(state["bypass_silver_index"], len(silver_labels) - 1),
        key="cost_diodes_bypass_silver",
    )
    bypass_silver_idx = int(bypass_silver_choice.split(":", 1)[0])
    state["bypass_silver_index"] = bypass_silver_idx
    bypass_silver_item = silver_items[bypass_silver_idx]

    col_tabs_geom = st.columns(2)
    with col_tabs_geom[0]:
        tab_length_mm = st.number_input(
            "Bypass tab length (mm)",
            min_value=0.1,
            step=0.1,
            value=float(state["bypass_tab_length_mm"]),
            key="cost_diodes_bypass_tab_length",
        )
        state["bypass_tab_length_mm"] = tab_length_mm
    with col_tabs_geom[1]:
        tab_width_mm = st.number_input(
            "Bypass tab width (mm)",
            min_value=0.1,
            step=0.1,
            value=float(state["bypass_tab_width_mm"]),
            key="cost_diodes_bypass_tab_width",
        )
        state["bypass_tab_width_mm"] = tab_width_mm

    bypass_yield_percent = st.slider(
        "Bypass process yield (%)",
        min_value=50,
        max_value=100,
        step=1,
        value=int(state["bypass_yield_percent"]),
        key="cost_diodes_bypass_yield",
    )
    state["bypass_yield_percent"] = bypass_yield_percent
    bypass_yield = bypass_yield_percent / 100.0

    tabs_per_bypass_diode = 2
    total_tab_length_per_diode_mm = tabs_per_bypass_diode * tab_length_mm

    cost_per_mm_bypass_tab = get_silver_cost_per_mm(
        bypass_silver_item,
        exchange_rate_gbp_per_usd=exchange_rate,
        override_width_mm=tab_width_mm,
    )
    silver_cost_per_bypass_diode = cost_per_mm_bypass_tab * total_tab_length_per_diode_mm

    weld_cost_per_bypass_diode = cost_per_weld_al + cost_per_weld_au

    raw_cost_per_bypass_diode = (
        price_bypass_gbp + silver_cost_per_bypass_diode + weld_cost_per_bypass_diode
    )

    if bypass_yield > 0:
        effective_cost_per_bypass_diode = raw_cost_per_bypass_diode / bypass_yield
    else:
        effective_cost_per_bypass_diode = 0.0

    total_bypass_cost = effective_cost_per_bypass_diode * num_cells

    st.markdown("##### Per bypass diode (before yield):")
    st.write(f"- Diode cost: **£{price_bypass_gbp:.2f}**")
    st.write(
        f"- Silver cost (2 tabs × {tab_length_mm:.2f} mm, width {tab_width_mm:.2f} mm): "
        f"**£{silver_cost_per_bypass_diode:.2f}**"
    )
    st.write(
        f"- Weld cost (1 × Weld_Head_Al + 1 × Weld_Head_Au): "
        f"**£{weld_cost_per_bypass_diode:.2f}**"
    )
    st.write(f"- Raw cost per bypass diode: **£{raw_cost_per_bypass_diode:.2f}**")

    st.markdown("##### Per bypass diode (after yield):")
    st.write(
        f"- Yield: **{bypass_yield_percent}%** → effective cost per good bypass diode: "
        f"**£{effective_cost_per_bypass_diode:.2f}**"
    )
    st.write(
        f"- Total for **{num_cells}** bypass diodes: "
        f"**£{total_bypass_cost:.2f}**"
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # BLOCKING DIODES
    # ---------------------------------------------------------
    st.subheader("Blocking Diodes")

    st.markdown(
        """
        - Always **2** blocking diodes per array  
        - Tab lengths come from array design (`blocking_tab_length1_mm` and `blocking_tab_length2_mm`)  
        - Silver width & material taken from array design  
        - Both welds use **Weld_Head_BL**  
        - Default yield ~90% (configurable)
        """
    )

    num_blocking_diodes = 2

    blocking_choice = st.selectbox(
        "Blocking diode material",
        diode_labels,
        index=min(state["blocking_diode_index"], len(diode_labels) - 1),
        key="cost_diodes_blocking_diode",
    )
    blocking_idx = int(blocking_choice.split(":", 1)[0])
    state["blocking_diode_index"] = blocking_idx
    blocking_diode_item = diode_items[blocking_idx]
    price_blocking_gbp = get_diode_price_gbp(blocking_diode_item, exchange_rate)

    block_silver_id = design.get("blocking_tab_silver_id", "")
    block_silver_width = float(design.get("blocking_tab_width_mm", 0.0))
    block_len1_mm = float(design.get("blocking_tab_length1_mm", 0.0))
    block_len2_mm = float(design.get("blocking_tab_length2_mm", 0.0))

    blocking_silver_item = find_material_by_id(silver_items, block_silver_id)

    if blocking_silver_item is None:
        st.error(
            "Blocking tab silver material not found in Silver Ribbon materials. "
            "Check `blocking_tab_silver_id` in the array design."
        )
        return

    blocking_yield_percent = st.slider(
        "Blocking process yield (%)",
        min_value=50,
        max_value=100,
        step=1,
        value=int(state["blocking_yield_percent"]),
        key="cost_diodes_blocking_yield",
    )
    state["blocking_yield_percent"] = blocking_yield_percent
    blocking_yield = blocking_yield_percent / 100.0

    total_blocking_tab_length_per_diode_mm = block_len1_mm + block_len2_mm

    cost_per_mm_blocking_tab = get_silver_cost_per_mm(
        blocking_silver_item,
        exchange_rate_gbp_per_usd=exchange_rate,
        override_width_mm=block_silver_width,
    )
    silver_cost_per_blocking_diode = (
        cost_per_mm_blocking_tab * total_blocking_tab_length_per_diode_mm
    )

    welds_per_blocking_diode = 2
    weld_cost_per_blocking_diode = welds_per_blocking_diode * cost_per_weld_bl

    raw_cost_per_blocking_diode = (
        price_blocking_gbp
        + silver_cost_per_blocking_diode
        + weld_cost_per_blocking_diode
    )

    if blocking_yield > 0:
        effective_cost_per_blocking_diode = raw_cost_per_blocking_diode / blocking_yield
    else:
        effective_cost_per_blocking_diode = 0.0

    total_blocking_cost = effective_cost_per_blocking_diode * num_blocking_diodes

    st.markdown("##### Per blocking diode (before yield):")
    st.write(f"- Diode cost: **£{price_blocking_gbp:.2f}**")
    st.write(
        f"- Silver cost (tabs {block_len1_mm:.2f} mm and {block_len2_mm:.2f} mm,"
        f" width {block_silver_width:.2f} mm): "
        f"**£{silver_cost_per_blocking_diode:.2f}**"
    )
    st.write(
        f"- Weld cost (2 × Weld_Head_BL): "
        f"**£{weld_cost_per_blocking_diode:.2f}**"
    )
    st.write(f"- Raw cost per blocking diode: **£{raw_cost_per_blocking_diode:.2f}**")

    st.markdown("##### Per blocking diode (after yield):")
    st.write(
        f"- Yield: **{blocking_yield_percent}%** → effective cost per good blocking diode: "
        f"**£{effective_cost_per_blocking_diode:.2f}**"
    )
    st.write(
        f"- Total for **{num_blocking_diodes}** blocking diodes: "
        f"**£{total_blocking_cost:2f}**"
    )

    st.markdown("---")

    total_diode_cost = total_bypass_cost + total_blocking_cost

    st.subheader("Total Diode Cost")

    st.write(f"**Total bypass diode cost:** £{total_bypass_cost:.2f}")
    st.write(f"**Total blocking diode cost:** £{total_blocking_cost:.2f}")
    st.write(f"**Total diode cost (bypass + blocking): £{total_diode_cost:.2f}**")

    if array_power > 0:
        st.write(
            f"**Cost per watt ({illumination}):** "
            f"£{(total_diode_cost / array_power):2f} per W"
        )
