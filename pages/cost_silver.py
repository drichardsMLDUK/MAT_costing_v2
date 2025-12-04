import streamlit as st
from model import load_materials, load_array_designs, load_product, MaterialItem
from pages.array_designs import compute_power_for_design


def get_silver_cost_per_mm(silver_item: MaterialItem, exchange_rate: float) -> float:
    """Compute cost per mm of silver in GBP from density, width, thickness."""
    try:
        price_per_g = float(silver_item.get("price_per_g", 0))
        currency = (silver_item.get("price_currency", "USD") or "USD").upper()
        width_mm = float(silver_item.get("width_mm", 0))
        thickness_mm = float(silver_item.get("thickness_mm", 0))
        density = float(silver_item.get("density_g_cm3", 0))
    except Exception:
        return 0.0

    if width_mm <= 0 or thickness_mm <= 0 or density <= 0:
        return 0.0

    if currency == "USD":
        price_gbp = price_per_g * exchange_rate
    else:
        price_gbp = price_per_g

    width_cm = width_mm / 10
    thickness_cm = thickness_mm / 10
    length_cm = 0.1   # 1 mm = 0.1 cm

    volume_cm3 = width_cm * thickness_cm * length_cm
    grams = volume_cm3 * density

    return grams * price_gbp


def render():
    st.title("Silver Cost")

    # ---------------------------------------------------------
    # Ensure array design selected
    # ---------------------------------------------------------
    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the Home page.")
        return

    selected = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # Load data
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd
    materials = load_materials()
    silver_items = materials.get("Silver Ribbon", [])
    designs = load_array_designs()
    design = next(d for d in designs if d["name"] == selected)

    if not silver_items:
        st.error("No silver items found in Materials → Silver Ribbon.")
        return

    # ---------------------------------------------------------
    # INITIALISE STATE (ONLY ONCE)
    # ---------------------------------------------------------
    if "cost_silver_state" not in st.session_state:
        st.session_state["cost_silver_state"] = {
            "top_tab_silver_index": 0,
            "top_tab_length_mm": 5.0,
        }

    state = st.session_state["cost_silver_state"]

    num_cells = design["num_cells"]
    top_tabs_count = 2 * (num_cells - 1)

    # Power calc
    power = compute_power_for_design(design)
    if illumination == "AM1.5":
        array_power = power["P_array_AM15_W"]
    else:
        array_power = power["P_array_AM0_W"]

    # ---------------------------------------------------------
    # TOP TABS
    # ---------------------------------------------------------
    st.subheader("Top Tabs")

    labels = [
        f"{i}: {item.get('id')} – {item.get('name')} ({item.get('width_mm')} mm)"
        for i, item in enumerate(silver_items)
    ]

    sel = st.selectbox(
        "Silver type for top tabs",
        labels,
        index=min(state["top_tab_silver_index"], len(labels)-1),
        key="cost_silver_top_tab_index",
    )
    idx = int(sel.split(":", 1)[0])
    state["top_tab_silver_index"] = idx
    tab_silver = silver_items[idx]

    tab_length_mm = st.number_input(
        "Top tab length (mm)",
        min_value=0.1,
        step=0.1,
        key="cost_silver_tab_length",
        value=float(state["top_tab_length_mm"]),
    )
    state["top_tab_length_mm"] = tab_length_mm

    cost_per_mm_tab = get_silver_cost_per_mm(tab_silver, exchange_rate)
    total_mm_tab = top_tabs_count * tab_length_mm
    total_cost_tab = total_mm_tab * cost_per_mm_tab

    st.write(f"Tabs needed: **{top_tabs_count}**")
    st.write(f"Total length: **{total_mm_tab:.2f} mm**")
    st.write(f"Cost: **£{total_cost_tab:.2f}**")

    st.markdown("---")

    # ---------------------------------------------------------
    # NEGATIVE END BARS
    # ---------------------------------------------------------
    st.subheader("Negative End Bars")

    neg_end_id = design["negative_end_silver_id"]
    neg_end_item = next((s for s in silver_items if s["id"] == neg_end_id), None)

    neg_end_length = design["negative_end_length_mm"]
    neg_end_width = design["negative_end_width_mm"]
    total_mm_end = neg_end_length * 2

    if neg_end_item:
        cost_end = get_silver_cost_per_mm(neg_end_item, exchange_rate) * total_mm_end
    else:
        st.error("Negative end silver not found in database.")
        cost_end = 0

    st.write(f"Length per bar: **{neg_end_length} mm**")
    st.write(f"Total (2 bars): **{total_mm_end} mm**")
    st.write(f"Cost: **£{cost_end:.2f}**")

    st.markdown("---")

    # ---------------------------------------------------------
    # NEGATIVE BAR
    # ---------------------------------------------------------
    st.subheader("Negative Bar")

    neg_bar_id = design["negative_bar_silver_id"]
    neg_bar_item = next((s for s in silver_items if s["id"] == neg_bar_id), None)

    neg_bar_length = design["negative_bar_length_mm"]
    neg_bar_width = design["negative_bar_width_mm"]

    if neg_bar_item:
        cost_bar = get_silver_cost_per_mm(neg_bar_item, exchange_rate) * neg_bar_length
    else:
        st.error("Negative bar silver not found in database.")
        cost_bar = 0

    st.write(f"Length: **{neg_bar_length} mm**")
    st.write(f"Cost: **£{cost_bar:.2f}**")

    st.markdown("---")

    # ---------------------------------------------------------
    # TOTALS
    # ---------------------------------------------------------
    total_cost = total_cost_tab + cost_end + cost_bar
    total_mm = total_mm_tab + total_mm_end + neg_bar_length

    st.subheader("Total Silver Usage")
    st.write(f"Total length used: **{total_mm:.2f} mm**")
    st.write(f"Total cost: **£{total_cost:.2f}**")

    if array_power > 0:
        st.write(
            f"Cost per W ({illumination}): **£{(total_cost/array_power):.2f} / W**"
        )
