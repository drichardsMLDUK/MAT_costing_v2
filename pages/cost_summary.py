import streamlit as st
import pandas as pd

from model import (
    load_array_designs,
    load_materials,
    load_product,
)
from pages.array_designs import compute_power_for_design


# ============================================================
# Shared helper functions (copied from individual pages)
# ============================================================

def get_silver_cost_per_mm(silver_item: dict, exchange_rate: float, override_width_mm: float | None = None) -> float:
    """Compute cost per mm of silver in GBP."""
    try:
        price_per_g = float(silver_item.get("price_per_g", 0))
        currency = (silver_item.get("price_currency", "USD") or "USD").upper()
        width_mm = float(
            override_width_mm if override_width_mm is not None else silver_item.get("width_mm", 0)
        )
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
    length_cm = 0.1  # 1 mm = 0.1 cm

    volume_cm3 = width_cm * thickness_cm * length_cm
    grams = volume_cm3 * density
    return grams * price_gbp


def get_diode_price_gbp(diode_item: dict, exchange_rate: float) -> float:
    """Return diode price in GBP."""
    currency = (diode_item.get("currency", "USD") or "USD").upper()
    try:
        if currency == "USD":
            unit_cost_usd = diode_item.get("unit_cost_usd", None)
            if unit_cost_usd is None:
                return 0.0
            return float(unit_cost_usd) * exchange_rate
        else:
            unit_cost_gbp = diode_item.get("unit_cost_gbp", None)
            if unit_cost_gbp is None:
                return 0.0
            return float(unit_cost_gbp)
    except (TypeError, ValueError):
        return 0.0


def get_weld_cost_per_weld(weld_item: dict, exchange_rate: float) -> float:
    """Compute cost per weld in GBP for a weld head."""
    currency = (weld_item.get("currency", "GBP") or "GBP").upper()
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
            total_cost_gbp = float(unit_cost_usd) * exchange_rate
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


def get_lamination_cost_per_m(item: dict, exchange_rate: float) -> float:
    """Lamination cost per meter (GBP)."""
    try:
        length_value = float(item.get("roll_length_value", 0.0))
        length_unit = (item.get("roll_length_unit", "m") or "m").lower()
    except Exception:
        return 0.0

    if length_value <= 0:
        return 0.0

    if length_unit in ("ft", "foot", "feet"):
        roll_length_m = length_value * 0.3048
    else:
        roll_length_m = length_value

    roll_cost_gbp = item.get("roll_cost_gbp", None)
    roll_cost_usd = item.get("roll_cost_usd", None)

    if roll_cost_gbp is not None:
        try:
            return float(roll_cost_gbp) / roll_length_m
        except Exception:
            return 0.0

    if roll_cost_usd is not None:
        try:
            return float(roll_cost_usd) * exchange_rate / roll_length_m
        except Exception:
            return 0.0

    return 0.0


def get_tape_cost_per_m(item: dict, exchange_rate: float) -> float:
    """Tape cost per meter (GBP)."""
    try:
        length_value = float(item.get("roll_length_value", 0.0))
        length_unit = (item.get("roll_length_unit", "m") or "m").lower()
    except Exception:
        return 0.0

    if length_value <= 0:
        return 0.0

    if length_unit in ("ft", "foot", "feet"):
        roll_length_m = length_value * 0.3048
    else:
        roll_length_m = length_value

    roll_cost_gbp = item.get("roll_cost_gbp", None)
    roll_cost_usd = item.get("roll_cost_usd", None)

    if roll_cost_gbp is not None:
        try:
            return float(roll_cost_gbp) / roll_length_m
        except Exception:
            return 0.0

    if roll_cost_usd is not None:
        try:
            return float(roll_cost_usd) * exchange_rate / roll_length_m
        except Exception:
            return 0.0

    return 0.0


def get_kapton_cost_per_disk(item: dict, exchange_rate: float) -> float:
    """Kapton insulation cost per disk in GBP."""
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
            total_cost_gbp = float(roll_cost_usd) * exchange_rate
            return total_cost_gbp / disks
        except (TypeError, ValueError):
            return 0.0

    return 0.0


def get_epoxy_cost_per_ml(item: dict, exchange_rate: float) -> float:
    """Epoxy cost per mL in GBP."""
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
            total_cost_gbp = float(total_cost_usd) * exchange_rate
            return total_cost_gbp / volume_ml
        except (TypeError, ValueError):
            return 0.0

    return 0.0


def get_unit_cost_gbp(item: dict, exchange_rate: float) -> float:
    """Unit cost in GBP for frame/board/box items."""
    currency = (item.get("currency", "GBP") or "GBP").upper()

    if "unit_cost_gbp" in item and item["unit_cost_gbp"] is not None:
        try:
            return float(item["unit_cost_gbp"])
        except (TypeError, ValueError):
            return 0.0

    if "unit_cost_usd" in item and item["unit_cost_usd"] is not None and currency == "USD":
        try:
            return float(item["unit_cost_usd"]) * exchange_rate
        except (TypeError, ValueError):
            return 0.0

    return 0.0


def get_foam_cost_per_piece(item: dict, exchange_rate: float) -> float:
    """Foam cost per piece in GBP."""
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
            return (float(total_cost_usd) * exchange_rate) / num_pieces
        except (TypeError, ValueError):
            return 0.0

    return 0.0


# ============================================================
# Main render
# ============================================================

def render():
    st.title("Cost Summary")

    if "selected_array_design" not in st.session_state:
        st.warning("Please choose an array design on the Home page first.")
        return

    selected_name = st.session_state["selected_array_design"]
    illumination = st.session_state.get("selected_illumination", "AM1.5")

    # Core data
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    designs = load_array_designs()
    design = next((d for d in designs if d["name"] == selected_name), None)
    if design is None:
        st.error("Selected array design not found.")
        return

    materials = load_materials()

    power = compute_power_for_design(design)
    array_power = power["P_array_AM15_W"] if illumination == "AM1.5" else power["P_array_AM0_W"]

    num_cells = int(design.get("num_cells", 0))
    if num_cells <= 0:
        st.error("Array design has invalid number of cells.")
        return

    # -----------------------------------------
    # Common geometry for length-based things
    # -----------------------------------------
    cell_h = float(design.get("cell_height_mm", 0.0))
    gap = float(design.get("gap_between_cells_mm", 0.0))
    pos_gap = float(design.get("positive_end_gap_mm", 0.0))
    neg_gap = float(design.get("negative_end_gap_mm", 0.0))

    base_length_mm = (
        cell_h * num_cells
        + gap * max(num_cells - 1, 0)
        + pos_gap
        + neg_gap
    )
    base_length_m = base_length_mm / 1000.0

    # ============================================================
    # 1) SILVER
    # ============================================================
    silver_items = materials.get("Silver Ribbon", [])
    silver_cost_total = 0.0

    if silver_items:
        # Grab state or defaults
        silver_state = st.session_state.get(
            "cost_silver_state",
            {"top_tab_silver_index": 0, "top_tab_length_mm": 5.0},
        )
        top_idx = min(silver_state["top_tab_silver_index"], len(silver_items) - 1)
        top_tab_item = silver_items[top_idx]
        tab_length_mm = float(silver_state["top_tab_length_mm"])

        top_tabs_count = 2 * (num_cells - 1)
        total_mm_tab = top_tabs_count * tab_length_mm
        cost_per_mm_tab = get_silver_cost_per_mm(top_tab_item, exchange_rate)
        cost_top_tabs = total_mm_tab * cost_per_mm_tab

        # Negative end bars (2 bars)
        neg_end_id = design.get("negative_end_silver_id", "")
        neg_end_len = float(design.get("negative_end_length_mm", 0.0))
        neg_end_item = find_material_by_id(silver_items, neg_end_id)
        if neg_end_item:
            total_mm_end = neg_end_len * 2
            cost_per_mm_end = get_silver_cost_per_mm(neg_end_item, exchange_rate)
            cost_neg_end = total_mm_end * cost_per_mm_end
        else:
            cost_neg_end = 0.0

        # Negative bar (1 bar)
        neg_bar_id = design.get("negative_bar_silver_id", "")
        neg_bar_len = float(design.get("negative_bar_length_mm", 0.0))
        neg_bar_item = find_material_by_id(silver_items, neg_bar_id)
        if neg_bar_item:
            cost_per_mm_bar = get_silver_cost_per_mm(neg_bar_item, exchange_rate)
            cost_neg_bar = neg_bar_len * cost_per_mm_bar
        else:
            cost_neg_bar = 0.0

        silver_cost_total = cost_top_tabs + cost_neg_end + cost_neg_bar

    # ============================================================
    # 2) DIODES (bypass + blocking)
    # ============================================================
    diodes_items = materials.get("Diodes", [])
    weld_items = materials.get("Weld heads", [])
    diodes_cost_total = 0.0

    if diodes_items and weld_items:
        diodes_state = st.session_state.get(
            "cost_diodes_state",
            {
                "bypass_diode_index": 0,
                "bypass_silver_index": 0,
                "bypass_tab_length_mm": 5.0,
                "bypass_tab_width_mm": 1.5,
                "bypass_yield_percent": 80,
                "blocking_diode_index": 0,
                "blocking_yield_percent": 90,
            },
        )

        # Weld heads needed
        weld_head_al = find_material_by_id(weld_items, "Weld_Head_Al")
        weld_head_au = find_material_by_id(weld_items, "Weld_Head_Au")
        weld_head_bl = find_material_by_id(weld_items, "Weld_Head_BL")

        if weld_head_al and weld_head_au and weld_head_bl and silver_items:
            cost_per_weld_al = get_weld_cost_per_weld(weld_head_al, exchange_rate)
            cost_per_weld_au = get_weld_cost_per_weld(weld_head_au, exchange_rate)
            cost_per_weld_bl = get_weld_cost_per_weld(weld_head_bl, exchange_rate)

            # --- Bypass diodes ---
            bypass_idx = min(diodes_state["bypass_diode_index"], len(diodes_items) - 1)
            bypass_diode_item = diodes_items[bypass_idx]
            price_bypass = get_diode_price_gbp(bypass_diode_item, exchange_rate)

            bypass_silver_idx = min(diodes_state["bypass_silver_index"], len(silver_items) - 1)
            bypass_silver_item = silver_items[bypass_silver_idx]

            tab_len = float(diodes_state["bypass_tab_length_mm"])
            tab_width = float(diodes_state["bypass_tab_width_mm"])
            bypass_yield = float(diodes_state["bypass_yield_percent"]) / 100.0

            tabs_per_bypass = 2
            total_tab_len_mm = tabs_per_bypass * tab_len
            cost_per_mm_bypass = get_silver_cost_per_mm(
                bypass_silver_item, exchange_rate, override_width_mm=tab_width
            )
            silver_cost_bypass = cost_per_mm_bypass * total_tab_len_mm
            weld_cost_bypass = cost_per_weld_al + cost_per_weld_au
            raw_cost_bypass = price_bypass + silver_cost_bypass + weld_cost_bypass
            eff_cost_bypass = raw_cost_bypass / bypass_yield if bypass_yield > 0 else 0.0
            total_bypass_cost = eff_cost_bypass * num_cells

            # --- Blocking diodes ---
            blocking_idx = min(diodes_state["blocking_diode_index"], len(diodes_items) - 1)
            blocking_diode_item = diodes_items[blocking_idx]
            price_blocking = get_diode_price_gbp(blocking_diode_item, exchange_rate)

            block_silver_id = design.get("blocking_tab_silver_id", "")
            block_silver_width = float(design.get("blocking_tab_width_mm", 0.0))
            block_len1 = float(design.get("blocking_tab_length1_mm", 0.0))
            block_len2 = float(design.get("blocking_tab_length2_mm", 0.0))
            blocking_yield = float(diodes_state["blocking_yield_percent"]) / 100.0

            blocking_silver_item = find_material_by_id(silver_items, block_silver_id)

            if blocking_silver_item:
                total_block_tab_len_mm = block_len1 + block_len2
                cost_per_mm_block = get_silver_cost_per_mm(
                    blocking_silver_item,
                    exchange_rate,
                    override_width_mm=block_silver_width,
                )
                silver_cost_block = cost_per_mm_block * total_block_tab_len_mm
                weld_cost_block = 2 * cost_per_weld_bl
                raw_cost_block = price_blocking + silver_cost_block + weld_cost_block
                eff_cost_block = raw_cost_block / blocking_yield if blocking_yield > 0 else 0.0
                total_blocking_cost = eff_cost_block * 2  # always 2 blocking diodes
            else:
                total_blocking_cost = 0.0

            diodes_cost_total = total_bypass_cost + total_blocking_cost

    # ============================================================
    # 3) WELD HEADS (Ag head for array welds only)
    # ============================================================
    weld_heads_cost_total = 0.0
    if weld_items:
        weld_head_ag = find_material_by_id(weld_items, "Weld_Head_Ag")
        if weld_head_ag:
            cost_per_weld_ag = get_weld_cost_per_weld(weld_head_ag, exchange_rate)

            # Top tabs: each tab has 4 welds, number of tabs = 2*(num_cells-1)
            top_tabs_count = 2 * (num_cells - 1)
            top_tab_welds = top_tabs_count * 4

            # Negative end: 8 welds; positive end: 4 welds
            neg_end_welds = 8
            pos_end_welds = 4

            # Bypass diodes welded to array: num_cells * 4
            bypass_array_welds = num_cells * 4

            total_welds = top_tab_welds + neg_end_welds + pos_end_welds + bypass_array_welds
            weld_heads_cost_total = total_welds * cost_per_weld_ag

    # ============================================================
    # 4) LAMINATION (3 layers + welding liner)
    # ============================================================
    lam_items = materials.get("Lamination", [])
    lamination_cost_total = 0.0

    if lam_items:
        lam_state = st.session_state.get(
            "cost_lamination_state",
            {
                "layer_indices": [0, 0, 0],
                "layer_waste_mm": [0.0, 0.0, 0.0],
                "liner_index": 0,
            },
        )

        layer_indices = lam_state["layer_indices"]
        layer_waste = lam_state["layer_waste_mm"]
        liner_index = lam_state["liner_index"]

        # Stack layers
        stack_cost = 0.0
        for i in range(3):
            idx = min(layer_indices[i], len(lam_items) - 1)
            item = lam_items[idx]
            waste_mm = float(layer_waste[i])

            total_len_mm = base_length_mm + waste_mm
            total_len_m = total_len_mm / 1000.0

            cost_per_m = get_lamination_cost_per_m(item, exchange_rate)
            stack_cost += cost_per_m * total_len_m

        # Liner (no waste, base length)
        liner_idx = min(liner_index, len(lam_items) - 1)
        liner_item = lam_items[liner_idx]
        liner_len_m = base_length_m
        liner_cost_per_m = get_lamination_cost_per_m(liner_item, exchange_rate)
        liner_cost = liner_cost_per_m * liner_len_m

        lamination_cost_total = stack_cost + liner_cost

    # ============================================================
    # 5) TAPES
    # ============================================================
    tapes_items = materials.get("Tapes", [])
    tapes_cost_total = 0.0

    if tapes_items:
        tapes_state = st.session_state.get(
            "cost_tapes_state",
            {
                "perimeter_tape_idx": 0,
                "other_tape_idx": 0,
                "other_length_mm": 0.0,
            },
        )

        perimeter_length_mm = 2 * base_length_mm + 140.0
        perimeter_length_m = perimeter_length_mm / 1000.0

        perim_idx = min(tapes_state["perimeter_tape_idx"], len(tapes_items) - 1)
        perim_item = tapes_items[perim_idx]
        cost_per_m_perim = get_tape_cost_per_m(perim_item, exchange_rate)
        cost_perimeter = cost_per_m_perim * perimeter_length_m

        other_idx = min(tapes_state["other_tape_idx"], len(tapes_items) - 1)
        other_item = tapes_items[other_idx]
        other_len_mm = float(tapes_state["other_length_mm"])
        other_len_m = other_len_mm / 1000.0
        cost_per_m_other = get_tape_cost_per_m(other_item, exchange_rate)
        cost_other = cost_per_m_other * other_len_m

        tapes_cost_total = cost_perimeter + cost_other

    # ============================================================
    # 6) MISC (Kapton + Epoxy)
    # ============================================================
    misc_items = materials.get("Misc", [])
    misc_cost_total = 0.0

    if misc_items:
        misc_state = st.session_state.get(
            "cost_misc_state",
            {
                "epoxy_index": 0,
                "epoxy_per_diode_ml": 0.0,
            },
        )

        # Kapton
        kapton_item = None
        for it in misc_items:
            if str(it.get("id", "")) == "Kapton_Insulation" or str(it.get("type", "")).lower() == "kapton":
                kapton_item = it
                break

        kapton_cost = 0.0
        if kapton_item:
            disks_per_array = num_cells  # one per bypass diode
            cost_per_disk = get_kapton_cost_per_disk(kapton_item, exchange_rate)
            kapton_cost = cost_per_disk * disks_per_array

        # Epoxy
        epoxy_items = [it for it in misc_items if str(it.get("type", "")).lower() == "epoxy"]
        epoxy_cost = 0.0
        if epoxy_items:
            epoxy_idx = min(misc_state["epoxy_index"], len(epoxy_items) - 1)
            epoxy_item = epoxy_items[epoxy_idx]
            per_diode_ml = float(misc_state["epoxy_per_diode_ml"])
            num_diodes_for_epoxy = 2
            total_epoxy_ml = per_diode_ml * num_diodes_for_epoxy
            cost_per_ml = get_epoxy_cost_per_ml(epoxy_item, exchange_rate)
            epoxy_cost = cost_per_ml * total_epoxy_ml

        misc_cost_total = kapton_cost + epoxy_cost

    # ============================================================
    # 7) PACKAGING
    # ============================================================
    packaging_items = materials.get("Packaging", [])
    packaging_cost_total = 0.0

    if packaging_items:
        pack_state = st.session_state.get(
            "cost_packaging_state",
            {
                "frame_idx": 0,
                "board_idx": 0,
                "box_idx": 0,
                "arrays_per_box": 4,
            },
        )

        frames = [it for it in packaging_items if str(it.get("type", "")).lower() == "frame"]
        boards = [it for it in packaging_items if str(it.get("type", "")).lower() == "shipping board"]
        foams = [it for it in packaging_items if str(it.get("type", "")).lower() == "foam"]
        boxes = [it for it in packaging_items if str(it.get("type", "")).lower() == "box"]

        if frames and boards and foams and boxes:
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

            if foam_3mm and foam_25mm:
                frame_idx = min(pack_state["frame_idx"], len(frames) - 1)
                board_idx = min(pack_state["board_idx"], len(boards) - 1)
                box_idx = min(pack_state["box_idx"], len(boxes) - 1)
                arrays_per_box = int(pack_state["arrays_per_box"])

                frame_item = frames[frame_idx]
                board_item = boards[board_idx]
                box_item = boxes[box_idx]

                frame_cost = get_unit_cost_gbp(frame_item, exchange_rate)
                board_cost = get_unit_cost_gbp(board_item, exchange_rate)
                box_cost = get_unit_cost_gbp(box_item, exchange_rate)

                foam_25_cost_piece = get_foam_cost_per_piece(foam_25mm, exchange_rate)
                foam_3_cost_piece = get_foam_cost_per_piece(foam_3mm, exchange_rate)

                foam_25_pieces = 2
                foam_3_pieces = max(arrays_per_box - 1, 0)

                foam_25_cost_box = foam_25_cost_piece * foam_25_pieces
                foam_3_cost_box = foam_3_cost_piece * foam_3_pieces
                foam_cost_box = foam_25_cost_box + foam_3_cost_box

                frame_board_per_array = frame_cost + board_cost
                shared_per_box = box_cost + foam_cost_box
                shared_per_array = shared_per_box / arrays_per_box

                packaging_cost_total = frame_board_per_array + shared_per_array

    # ============================================================
    # BUILD SUMMARY TABLE
    # ============================================================
    rows = []

    def add_row(name: str, cost: float):
        if cost is None:
            cost_val = 0.0
        else:
            cost_val = float(cost)
        if array_power > 0:
            cpw = cost_val / array_power
        else:
            cpw = 0.0
        rows.append(
            {
                "Category": name,
                "Cost per array [£]": cost_val,
                "Cost per W [£/W]": cpw,
            }
        )

    add_row("Silver", silver_cost_total)
    add_row("Diodes", diodes_cost_total)
    add_row("Weld heads", weld_heads_cost_total)
    add_row("Lamination", lamination_cost_total)
    add_row("Tapes", tapes_cost_total)
    add_row("Misc", misc_cost_total)
    add_row("Packaging", packaging_cost_total)

    df = pd.DataFrame(rows)

    # ------- Display table with 2 dp + centred numeric columns -------
    st.subheader("Cost Breakdown per Array")

    df_display = df.copy()
    df_display["Cost per array [£]"] = df_display["Cost per array [£]"].round(2)
    df_display["Cost per W [£/W]"] = df_display["Cost per W [£/W]"].round(2)

    styler = (
        df_display.style
        .format(
            {
                "Cost per array [£]": "{:.2f}",
                "Cost per W [£/W]": "{:.2f}",
            }
        )
        .set_properties(
            **{"text-align": "center"},
            subset=["Cost per array [£]", "Cost per W [£/W]"],
        )
    )

    st.table(styler)

    # ------- Bar chart: cost per array by category -------
        # ------- Bar chart: cost per array by category -------
        # ------- Bar chart: cost per array by category -------
    st.subheader("Cost Breakdown (per array)")

    chart_df = df.copy()

    # Rename to chart-safe column names
    chart_df = chart_df.rename(
        columns={
            "Cost per array [£]": "cost_array",
            "Cost per W [£/W]": "cost_watt",
            "Category": "category"
        }
    )

    # Force numeric
    chart_df["cost_array"] = pd.to_numeric(chart_df["cost_array"], errors="coerce")

    # If everything is zero or NaN, show message
    if chart_df["cost_array"].isna().all() or chart_df["cost_array"].sum() == 0:
        st.info("No valid cost data to plot.")
    else:
        # Clean DataFrame for charting
        chart_data = chart_df[["category", "cost_array"]]

        # Real chart (this will work with new Streamlit)
        st.bar_chart(
            chart_data,
            x="category",
            y="cost_array",
            width="stretch",
            height=400,
        )



    total_cost = df["Cost per array [£]"].sum()
    total_cost_per_w = total_cost / array_power if array_power > 0 else 0.0

    st.markdown("---")
    st.subheader("Totals")
    st.write(f"**Total cost per array:** £{total_cost:.2f}")
    st.write(f"**Total cost per W ({illumination}):** £{total_cost_per_w:.2f} / W")

    # ============================================================
    # Expose totals to other pages (Home scenarios, etc.)
    # ============================================================
    st.session_state["materials_cost_per_array"] = total_cost
    st.session_state["materials_cost_breakdown"] = rows
