import streamlit as st

from model import load_array_designs, load_materials, load_product
from pages.array_designs import compute_power_for_design


# ============================================================
# Helper functions
# ============================================================

def get_unit_cost_gbp(item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """
    Get a unit cost in GBP for frame/board/box items.

    Supports:
    - unit_cost_gbp (preferred)
    - unit_cost_usd + currency == USD
    """
    currency = (item.get("currency", "GBP") or "GBP").upper()

    if "unit_cost_gbp" in item and item["unit_cost_gbp"] is not None:
        try:
            return float(item["unit_cost_gbp"])
        except (TypeError, ValueError):
            return 0.0

    if "unit_cost_usd" in item and item["unit_cost_usd"] is not None and currency == "USD":
        try:
            return float(item["unit_cost_usd"]) * float(exchange_rate_gbp_per_usd)
        except (TypeError, ValueError):
            return 0.0

    return 0.0


def get_foam_cost_per_piece(item: dict, exchange_rate_gbp_per_usd: float) -> float:
    """
    Foam cost per piece (GBP).

    Supports:
    - num_pieces
    - total_cost_gbp (preferred)
    - total_cost_usd + currency == USD
    """
    num_pieces = item.get("num_pieces", None)
    if not num_pieces:
        return 0.0

    try:
        num_pieces = float(num_pieces)
    except (TypeError, ValueError):
        return 0.0

    if num_pieces <= 0:
        return 0.0

    currency = (item.get("currency", "GBP") or "GBP").upper()

    total_cost_gbp = item.get("total_cost_gbp", None)
    if total_cost_gbp is not None:
        try:
            return float(total_cost_gbp) / num_pieces
        except (TypeError, ValueError):
            return 0.0

    total_cost_usd = item.get("total_cost_usd", None)
    if total_cost_usd is not None and currency == "USD":
        try:
            return (float(total_cost_usd) * exchange_rate_gbp_per_usd) / num_pieces
        except (TypeError, ValueError):
            return 0.0

    return 0.0


# ============================================================
# Main render
# ============================================================

def render():
    st.title("Packaging Cost")

    # ---------------------------------------------------------
    # Ensure array design selected
    # ---------------------------------------------------------
    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the Home page first.")
        return

    selected_name = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # ---------------------------------------------------------
    # Load core data
    # ---------------------------------------------------------
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    designs = load_array_designs()
    design = next((d for d in designs if d["name"] == selected_name), None)

    if design is None:
        st.error("Selected array design not found.")
        return

    materials = load_materials()
    packaging_items = materials.get("Packaging", [])

    if not packaging_items:
        st.error("No Packaging materials found. Add some under Materials → Packaging.")
        return

    # Power
    power = compute_power_for_design(design)
    array_power = (
        power["P_array_AM15_W"]
        if illumination == "AM1.5"
        else power["P_array_AM0_W"]
    )

    # ---------------------------------------------------------
    # Categorise packaging items
    # ---------------------------------------------------------
    frames = [it for it in packaging_items if str(it.get("type", "")).lower() == "frame"]
    boards = [it for it in packaging_items if str(it.get("type", "")).lower() == "shipping board"]
    foams = [it for it in packaging_items if str(it.get("type", "")).lower() == "foam"]
    boxes = [it for it in packaging_items if str(it.get("type", "")).lower() == "box"]

    if not frames:
        st.error("No frames found in Packaging (type 'Frame').")
        return
    if not boards:
        st.error("No shipping boards found in Packaging (type 'Shipping board').")
        return
    if not foams:
        st.error("No foam items found in Packaging (type 'Foam').")
        return
    if not boxes:
        st.error("No box items found in Packaging (type 'Box').")
        return

    # Separate 3mm and 25mm foam
    foam_3mm = None
    foam_25mm = None
    for f in foams:
        try:
            th = float(f.get("thickness_mm", 0.0))
        except (TypeError, ValueError):
            th = 0.0
        if abs(th - 3.0) < 1e-3:
            foam_3mm = f
        elif abs(th - 25.0) < 1e-3:
            foam_25mm = f

    if foam_3mm is None or foam_25mm is None:
        st.error(
            "Expected both 3mm and 25mm foam in Packaging (type 'Foam' with thickness_mm 3.0 and 25.0)."
        )
        return

    # ---------------------------------------------------------
    # Initialise persistent state
    # ---------------------------------------------------------
    if "cost_packaging_state" not in st.session_state:
        st.session_state["cost_packaging_state"] = {
            "frame_idx": 0,
            "board_idx": 0,
            "box_idx": 0,
            "arrays_per_box": 4,
        }

    state = st.session_state["cost_packaging_state"]

    # Build labels
    frame_labels = [
        f"{i}: {it.get('id','(no id)')} – {it.get('name','(no name)')}"
        for i, it in enumerate(frames)
    ]
    board_labels = [
        f"{i}: {it.get('id','(no id)')} – {it.get('name','(no name)')}"
        for i, it in enumerate(boards)
    ]
    box_labels = [
        f"{i}: {it.get('id','(no id)')} – {it.get('name','(no name)')} "
        f"({it.get('diameter_mm','?')} mm diameter)"
        for i, it in enumerate(boxes)
    ]

    # ---------------------------------------------------------
    # Frame & Board (per array)
    # ---------------------------------------------------------
    st.subheader("Frame and Board per Array")

    current_frame_idx = min(state["frame_idx"], len(frame_labels) - 1)
    frame_sel = st.selectbox(
        "Select frame",
        frame_labels,
        index=current_frame_idx,
        key="cost_packaging_frame_select",
    )
    frame_idx = int(frame_sel.split(":", 1)[0])
    state["frame_idx"] = frame_idx
    frame_item = frames[frame_idx]
    frame_cost = get_unit_cost_gbp(frame_item, exchange_rate)

    current_board_idx = min(state["board_idx"], len(board_labels) - 1)
    board_sel = st.selectbox(
        "Select shipping board",
        board_labels,
        index=current_board_idx,
        key="cost_packaging_board_select",
    )
    board_idx = int(board_sel.split(":", 1)[0])
    state["board_idx"] = board_idx
    board_item = boards[board_idx]
    board_cost = get_unit_cost_gbp(board_item, exchange_rate)

    st.write(
        f"- Frame: **{frame_item.get('name','(no name)')}** "
        f"(id: {frame_item.get('id','')}) – **£{frame_cost:.2f}** per array"
    )
    st.write(
        f"- Board: **{board_item.get('name','(no name)')}** "
        f"(id: {board_item.get('id','')}) – **£{board_cost:.2f}** per array"
    )

    st.markdown("---")

    # ---------------------------------------------------------
    # Box + Foam (per box)
    # ---------------------------------------------------------
    st.subheader("Box and Foam per Box")

    current_box_idx = min(state["box_idx"], len(box_labels) - 1)
    box_sel = st.selectbox(
        "Select box type",
        box_labels,
        index=current_box_idx,
        key="cost_packaging_box_select",
    )
    box_idx = int(box_sel.split(":", 1)[0])
    state["box_idx"] = box_idx
    box_item = boxes[box_idx]
    box_cost = get_unit_cost_gbp(box_item, exchange_rate)

    arrays_per_box = st.number_input(
        "Number of arrays per box",
        min_value=1,
        step=1,
        key="cost_packaging_arrays_per_box",
        value=int(state["arrays_per_box"]),
    )
    state["arrays_per_box"] = arrays_per_box

    # Foam usage:
    #  - 25mm foam: 2 pieces per box (top + bottom)
    #  - 3mm foam: (arrays_per_box - 1) pieces between arrays
    foam_25_pieces = 2
    foam_3_pieces = max(arrays_per_box - 1, 0)

    foam_25_cost_per_piece = get_foam_cost_per_piece(foam_25mm, exchange_rate)
    foam_3_cost_per_piece = get_foam_cost_per_piece(foam_3mm, exchange_rate)

    foam_25_cost_box = foam_25_cost_per_piece * foam_25_pieces
    foam_3_cost_box = foam_3_cost_per_piece * foam_3_pieces
    total_foam_cost_box = foam_25_cost_box + foam_3_cost_box

    st.write(
        f"- Box: **{box_item.get('name','(no name)')}** "
        f"(id: {box_item.get('id','')}, diameter {box_item.get('diameter_mm','?')} mm) "
        f"– **£{box_cost:.2f}** per box"
    )
    st.write(
        f"- 25mm foam pieces per box: **{foam_25_pieces}** → cost **£{foam_25_cost_box:.2f}**"
    )
    st.write(
        f"- 3mm foam pieces per box: **{foam_3_pieces}** → cost **£{foam_3_cost_box:.2f}**"
    )
    st.write(f"- Total foam cost per box: **£{total_foam_cost_box:.2f}**")

    st.markdown("---")

    # ---------------------------------------------------------
    # Total packaging cost per array
    # ---------------------------------------------------------
    st.subheader("Total Packaging Cost per Array")

    frame_board_per_array = frame_cost + board_cost
    shared_per_box = box_cost + total_foam_cost_box
    shared_per_array = shared_per_box / arrays_per_box

    total_packaging_per_array = frame_board_per_array + shared_per_array

    st.write(f"- Frame + board per array: **£{frame_board_per_array:.2f}**")
    st.write(
        f"- Box + foam per array (shared): **£{shared_per_array:.2f}** "
        f"(with {arrays_per_box} arrays per box)"
    )
    st.write(f"**Total packaging cost per array:** **£{total_packaging_per_array:.2f}**")

    if array_power > 0:
        cost_per_watt = total_packaging_per_array / array_power
        st.write(
            f"**Packaging cost per watt ({illumination}):** "
            f"£{cost_per_watt:.5f} / W"
        )
