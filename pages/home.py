import os
from math import ceil

import streamlit as st

from model import load_array_designs, load_materials
from pages.array_designs import compute_power_for_design

# NEW: import labour helpers
from labour_model import load_process_steps, load_operator_profiles

# Folder for design images (e.g. images/11_cell.png)
IMAGE_FOLDER = "images"


def _find_material_by_id(items: list[dict], mat_id: str | None) -> dict | None:
    if not mat_id:
        return None
    for item in items:
        if str(item.get("id", "")) == str(mat_id):
            return item
    return None


def _compute_base_length_m(design: dict, num_cells: int) -> tuple[float, float]:
    """Return (base_length_mm, base_length_m) for lam/tape geometry."""
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
    return base_length_mm, base_length_mm / 1000.0


def _render_material_requirements_expander(
    title: str,
    arrays_to_build: int,
    design: dict,
    materials: dict,
):
    """Show material quantities for the given scenario (arrays_to_build)."""
    if arrays_to_build <= 0:
        return

    num_cells = int(design.get("num_cells", 0))
    if num_cells <= 0:
        return

    base_length_mm, base_length_m = _compute_base_length_m(design, num_cells)

    with st.expander(title, expanded=False):
        st.caption(
            "Quantities below are based on the **number of arrays to build** "
            "(including scrap implied by the yield)."
        )

        # ------------------------------------------------------------------
        # 1) SILVER RIBBON
        # ------------------------------------------------------------------
        silver_items = materials.get("Silver Ribbon", [])
        st.markdown("##### Silver ribbon (total length per item)")

        if silver_items:
            silver_usage_m = {}  # key -> total length [m]
            silver_meta = {}     # key -> (name, width_mm)

            # Helper to accumulate length for a given silver item
            def add_silver_len(item: dict, length_m: float):
                if item is None or length_m <= 0:
                    return
                key = str(item.get("id", item.get("name", "unknown")))
                name = item.get("name", "Unnamed")
                width_mm = item.get("width_mm", None)
                silver_usage_m[key] = silver_usage_m.get(key, 0.0) + length_m
                if key not in silver_meta:
                    silver_meta[key] = (name, width_mm)

            # --- Top tabs (from cost_silver_state) ---
            silver_state = st.session_state.get(
                "cost_silver_state",
                {"top_tab_silver_index": 0, "top_tab_length_mm": 5.0},
            )
            top_idx = (
                min(silver_state["top_tab_silver_index"], len(silver_items) - 1)
                if silver_items
                else 0
            )
            if silver_items:
                top_tab_item = silver_items[top_idx]
                tab_length_mm = float(silver_state.get("top_tab_length_mm", 5.0))
                top_tabs_count = 2 * (num_cells - 1)
                per_array_mm_top = top_tabs_count * tab_length_mm
                total_mm_top = per_array_mm_top * arrays_to_build
                add_silver_len(top_tab_item, total_mm_top / 1000.0)

            # --- Negative end bars (2 bars) ---
            neg_end_id = design.get("negative_end_silver_id", "")
            neg_end_len = float(design.get("negative_end_length_mm", 0.0))
            neg_end_item = _find_material_by_id(silver_items, neg_end_id)
            if neg_end_item and neg_end_len > 0:
                per_array_mm_neg_end = neg_end_len * 2.0
                total_mm_neg_end = per_array_mm_neg_end * arrays_to_build
                add_silver_len(neg_end_item, total_mm_neg_end / 1000.0)

            # --- Negative bar (1 bar) ---
            neg_bar_id = design.get("negative_bar_silver_id", "")
            neg_bar_len = float(design.get("negative_bar_length_mm", 0.0))
            neg_bar_item = _find_material_by_id(silver_items, neg_bar_id)
            if neg_bar_item and neg_bar_len > 0:
                per_array_mm_neg_bar = neg_bar_len
                total_mm_neg_bar = per_array_mm_neg_bar * arrays_to_build
                add_silver_len(neg_bar_item, total_mm_neg_bar / 1000.0)

            # --- Diode tab silver from diodes state ---
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

            # Bypass diode tabs
            if silver_items:
                bypass_silver_idx = min(
                    diodes_state["bypass_silver_index"], len(silver_items) - 1
                )
                bypass_silver_item = silver_items[bypass_silver_idx]
                tab_len = float(diodes_state.get("bypass_tab_length_mm", 5.0))
                tabs_per_bypass = 2
                per_diode_mm_tabs = tabs_per_bypass * tab_len
                bypass_diodes_per_array = num_cells
                per_array_mm_bypass_tabs = per_diode_mm_tabs * bypass_diodes_per_array
                total_mm_bypass_tabs = per_array_mm_bypass_tabs * arrays_to_build
                add_silver_len(bypass_silver_item, total_mm_bypass_tabs / 1000.0)

            # Blocking diode tabs
            block_silver_id = design.get("blocking_tab_silver_id", "")
            block_len1 = float(design.get("blocking_tab_length1_mm", 0.0))
            block_len2 = float(design.get("blocking_tab_length2_mm", 0.0))
            blocking_silver_item = _find_material_by_id(silver_items, block_silver_id)
            if blocking_silver_item and (block_len1 > 0 or block_len2 > 0):
                total_block_tab_len_mm = block_len1 + block_len2
                blocking_diodes_per_array = 2  # fixed in cost_summary
                per_array_mm_block_tabs = (
                    total_block_tab_len_mm * blocking_diodes_per_array
                )
                total_mm_block_tabs = per_array_mm_block_tabs * arrays_to_build
                add_silver_len(blocking_silver_item, total_mm_block_tabs / 1000.0)

            if silver_usage_m:
                rows = []
                for key, total_m in silver_usage_m.items():
                    name, width_mm = silver_meta.get(key, ("Unnamed", None))
                    per_array_m = total_m / arrays_to_build
                    rows.append(
                        {
                            "Silver item": name,
                            "Width [mm]": width_mm,
                            "Per array [m]": round(per_array_m, 4),
                            "Total [m]": round(total_m, 2),
                        }
                    )
                st.table(rows)
            else:
                st.info("No silver usage could be determined for this scenario.")
        else:
            st.info("No silver ribbon materials found in the database.")

        # ------------------------------------------------------------------
        # 2) WELD HEADS (weld counts)
        # ------------------------------------------------------------------
        st.markdown("##### Welds (by weld head type)")

        # Bypass diode welds (Al & Au) – inferred from cost_summary logic
        welds_al_per_array = num_cells  # 1 Al weld per bypass diode
        welds_au_per_array = num_cells  # 1 Au weld per bypass diode

        # Blocking diode welds (BL): 2 welds per blocking diode, 2 diodes per array
        welds_bl_per_array = 2 * 2  # 4 BL welds per array

        # Array welds (Ag), from cost_summary
        top_tabs_count = 2 * (num_cells - 1)
        top_tab_welds = top_tabs_count * 4
        neg_end_welds = 8
        pos_end_welds = 4
        bypass_array_welds = num_cells * 4
        welds_ag_per_array = (
            top_tab_welds + neg_end_welds + pos_end_welds + bypass_array_welds
        )

        welds_rows = [
            {
                "Weld head": "Al",
                "Per array [welds]": welds_al_per_array,
                "Total [welds]": welds_al_per_array * arrays_to_build,
            },
            {
                "Weld head": "Au",
                "Per array [welds]": welds_au_per_array,
                "Total [welds]": welds_au_per_array * arrays_to_build,
            },
            {
                "Weld head": "BL",
                "Per array [welds]": welds_bl_per_array,
                "Total [welds]": welds_bl_per_array * arrays_to_build,
            },
            {
                "Weld head": "Ag",
                "Per array [welds]": welds_ag_per_array,
                "Total [welds]": welds_ag_per_array * arrays_to_build,
            },
        ]
        st.table(welds_rows)

        # ------------------------------------------------------------------
        # 3) DIODES + KAPTON + EPOXY
        # ------------------------------------------------------------------
        misc_items = materials.get("Misc", [])

        total_bypass_diodes = num_cells * arrays_to_build
        total_blocking_diodes = 2 * arrays_to_build

        # Kapton disks (assumed 1 per bypass diode)
        kapton_disks_total = 0
        epoxy_total_ml = 0.0

        if misc_items:
            # Kapton
            kapton_item = None
            for it in misc_items:
                if (
                    str(it.get("id", "")) == "Kapton_Insulation"
                    or str(it.get("type", "")).lower() == "kapton"
                ):
                    kapton_item = it
                    break

            if kapton_item:
                kapton_disks_total = total_bypass_diodes

            # Epoxy
            misc_state = st.session_state.get(
                "cost_misc_state",
                {
                    "epoxy_index": 0,
                    "epoxy_per_diode_ml": 0.0,
                },
            )
            per_diode_ml = float(misc_state.get("epoxy_per_diode_ml", 0.0))
            num_diodes_for_epoxy = 2  # same assumption as cost_summary
            epoxy_per_array_ml = per_diode_ml * num_diodes_for_epoxy
            epoxy_total_ml = epoxy_per_array_ml * arrays_to_build

        st.markdown("##### Diodes & Insulation")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            st.metric("Bypass diodes", f"{total_bypass_diodes}")
        with col_d2:
            st.metric("Blocking diodes", f"{total_blocking_diodes}")
        with col_d3:
            st.metric("Kapton disks", f"{kapton_disks_total}")
        with col_d4:
            st.metric("Epoxy volume", f"{epoxy_total_ml:.1f} mL")

        # ------------------------------------------------------------------
        # 4) LAMINATION (3 layers + liner)
        # ------------------------------------------------------------------
        lam_items = materials.get("Lamination", [])
        st.markdown("##### Lamination films")

        if lam_items:
            lam_state = st.session_state.get(
                "cost_lamination_state",
                {
                    "layer_indices": [0, 0, 0],
                    "layer_waste_mm": [0.0, 0.0, 0.0],
                    "liner_index": 0,
                },
            )
            layer_indices = lam_state.get("layer_indices", [0, 0, 0])
            layer_waste = lam_state.get("layer_waste_mm", [0.0, 0.0, 0.0])
            liner_index = lam_state.get("liner_index", 0)

            layer_rows = []

            # 3 stack layers
            for i in range(3):
                if not lam_items:
                    continue
                idx = min(layer_indices[i], len(lam_items) - 1)
                item = lam_items[idx]
                waste_mm = float(layer_waste[i])

                per_array_len_mm = base_length_mm + waste_mm
                per_array_len_m = per_array_len_mm / 1000.0
                total_len_m = per_array_len_m * arrays_to_build

                layer_rows.append(
                    {
                        "Layer": f"Layer {i+1} – {item.get('name', 'Unnamed')}",
                        "Per array [m]": round(per_array_len_m, 4),
                        "Total [m]": round(total_len_m, 2),
                    }
                )

            # Liner (no waste)
            if lam_items:
                liner_idx = min(liner_index, len(lam_items) - 1)
                liner_item = lam_items[liner_idx]
                per_array_liner_m = base_length_m
                total_liner_m = per_array_liner_m * arrays_to_build

                layer_rows.append(
                    {
                        "Layer": f"Liner – {liner_item.get('name', 'Unnamed')}",
                        "Per array [m]": round(per_array_liner_m, 4),
                        "Total [m]": round(total_liner_m, 2),
                    }
                )

            if layer_rows:
                st.table(layer_rows)
            else:
                st.info("No lamination layers configured yet.")
        else:
            st.info("No lamination materials found in the database.")

        # ------------------------------------------------------------------
        # 5) TAPES
        # ------------------------------------------------------------------
        tapes_items = materials.get("Tapes", [])
        st.markdown("##### Tapes")

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
            total_perim_m = perimeter_length_m * arrays_to_build

            perim_idx = min(tapes_state["perimeter_tape_idx"], len(tapes_items) - 1)
            perim_item = tapes_items[perim_idx]

            other_idx = min(tapes_state["other_tape_idx"], len(tapes_items) - 1)
            other_item = tapes_items[other_idx]
            other_len_mm = float(tapes_state["other_length_mm"])
            other_len_m = other_len_mm / 1000.0
            total_other_m = other_len_m * arrays_to_build

            tape_rows = [
                {
                    "Tape": f"Perimeter – {perim_item.get('name', 'Unnamed')}",
                    "Per array [m]": round(perimeter_length_m, 4),
                    "Total [m]": round(total_perim_m, 2),
                },
                {
                    "Tape": f"Other – {other_item.get('name', 'Unnamed')}",
                    "Per array [m]": round(other_len_m, 4),
                    "Total [m]": round(total_other_m, 2),
                },
            ]
            st.table(tape_rows)
        else:
            st.info("No tape materials found in the database.")

        # ------------------------------------------------------------------
        # 6) PACKAGING (frames, boards, boxes, foams)
        # ------------------------------------------------------------------
        packaging_items = materials.get("Packaging", [])
        st.markdown("##### Packaging")

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

            frames = [
                it for it in packaging_items
                if str(it.get("type", "")).lower() == "frame"
            ]
            boards = [
                it for it in packaging_items
                if str(it.get("type", "")).lower() == "shipping board"
            ]
            foams = [
                it for it in packaging_items
                if str(it.get("type", "")).lower() == "foam"
            ]
            boxes = [
                it for it in packaging_items
                if str(it.get("type", "")).lower() == "box"
            ]

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

                    frames_needed = arrays_to_build
                    boards_needed = arrays_to_build
                    boxes_needed = (
                        ceil(arrays_to_build / arrays_per_box)
                        if arrays_per_box > 0
                        else 0
                    )

                    foam_25_pieces_per_box = 2
                    foam_3_pieces_per_box = max(arrays_per_box - 1, 0)

                    foam_25_total = boxes_needed * foam_25_pieces_per_box
                    foam_3_total = boxes_needed * foam_3_pieces_per_box

                    pack_rows = [
                        {
                            "Item": f"Frames – {frame_item.get('name', 'Unnamed')}",
                            "Quantity": frames_needed,
                        },
                        {
                            "Item": f"Boards – {board_item.get('name', 'Unnamed')}",
                            "Quantity": boards_needed,
                        },
                        {
                            "Item": f"Boxes – {box_item.get('name', 'Unnamed')}",
                            "Quantity": boxes_needed,
                        },
                        {
                            "Item": (
                                f"Foam 25 mm – {foam_25mm.get('name', '25 mm foam')}"
                            ),
                            "Quantity": foam_25_total,
                        },
                        {
                            "Item": (
                                f"Foam 3 mm – {foam_3mm.get('name', '3 mm foam')}"
                            ),
                            "Quantity": foam_3_total,
                        },
                    ]
                    st.table(pack_rows)
                else:
                    st.info(
                        "Foam pieces not fully configured (need both 3 mm and 25 mm types)."
                    )
            else:
                st.info("Frames/boards/foams/boxes not fully configured for packaging.")
        else:
            st.info("No packaging materials found in the database.")


# NEW: helper to compute labour time & cost per array
def _compute_labour_per_array(num_cells: int) -> tuple[float, float]:
    """
    Returns (labour_time_per_array_s, labour_cost_per_array).

    Uses:
    - process.yaml: time_per_unit_s and timing_basis, operators
    - operator_profiles.yaml: hourly_rate

    Currently includes:
    - steps with timing_basis == 'cell' or 'array' (both are per cell after normalisation)
    Ignores diode-basis steps for now.
    """
    if num_cells <= 0:
        return 0.0, 0.0

    try:
        steps = load_process_steps()
        operators = load_operator_profiles()
    except Exception:
        return 0.0, 0.0

    total_time_per_cell_s = 0.0
    total_cost_per_cell = 0.0

    for step in steps:
        basis = str(step.get("timing_basis", "cell")).lower()
        if basis not in ("cell", "array"):
            # diode-basis or unknown → handled later if needed
            continue

        time_per_unit_s = float(step.get("time_per_unit_s", 0.0))
        if time_per_unit_s <= 0:
            continue

        # sum hourly rates of assigned operators
        op_ids = [
            op.get("operator_id")
            for op in step.get("operators", [])
            if isinstance(op, dict) and op.get("operator_id")
        ]
        total_hourly_rate = 0.0
        for oid in op_ids:
            op_profile = operators.get(oid)
            if op_profile is None:
                continue
            # handle both dataclass and dict-like profiles
            rate = getattr(op_profile, "hourly_rate", None)
            if rate is None:
                try:
                    rate = float(op_profile.get("hourly_rate", 0.0))  # type: ignore[attr-defined]
                except Exception:
                    rate = 0.0
            total_hourly_rate += float(rate)

        # time & cost per cell for this step
        total_time_per_cell_s += time_per_unit_s
        if total_hourly_rate > 0:
            total_cost_per_cell += time_per_unit_s * total_hourly_rate / 3600.0

    labour_time_per_array_s = total_time_per_cell_s * num_cells
    labour_cost_per_array = total_cost_per_cell * num_cells

    return labour_time_per_array_s, labour_cost_per_array


def _render_design_image(design: dict):
    """Show the design image at the top of the page based on num_cells."""
    try:
        num_cells = int(design.get("num_cells", 0))
    except (TypeError, ValueError):
        num_cells = 0

    if num_cells <= 0:
        return

    filename = f"{num_cells}_cell.png"
    image_path = os.path.join(IMAGE_FOLDER, filename)

    if os.path.exists(image_path):
        st.image(
            image_path,
            caption=f"{num_cells}-cell string layout",
            use_container_width=True,
        )
    else:
        st.info(
            f"Design image not found for {num_cells} cells "
            f"(`{filename}` in `{IMAGE_FOLDER}`)"
        )


def render():
    # Small style tweak for a cleaner feel
    st.markdown(
        """
        <style>
        .section-card {
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            border: 1px solid rgba(200,200,255,0.2);
            background-color: rgba(0,0,101,0.05);
            margin-bottom: 1rem;
        }
        .section-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Home – Array Overview")

    st.markdown(
        """
        Quickly visualise an array design, then explore customer order scenarios
        based on **power requirement** or **budget**, with yield, materials and
        labour impact all in one place.
        """
    )

    # -----------------------------------------------------------
    # Load designs & materials
    # -----------------------------------------------------------
    designs = load_array_designs()

    if not designs:
        st.warning(
            "No array designs found. Please add one under **Array Designs**."
        )
        return

    materials = load_materials()
    design_names = [d["name"] for d in designs]

    # -----------------------------------------------------------
    # Restore previous selections from session_state (if any)
    # -----------------------------------------------------------

    # Array design
    saved_design_name = st.session_state.get("selected_array_design", design_names[0])
    if saved_design_name not in design_names:
        saved_design_name = design_names[0]
    default_design_index = design_names.index(saved_design_name)

    # Illumination condition
    illum_options = ("AM1.5", "AM0")
    saved_illumination = st.session_state.get("selected_illumination", "AM1.5")
    if saved_illumination not in illum_options:
        saved_illumination = "AM1.5"
    default_illum_index = illum_options.index(saved_illumination)

    # Yield
    saved_yield = st.session_state.get("home_yield", 0.90)

    # Power scenario inputs
    unit_options = ("W", "kW")
    saved_target_power = float(st.session_state.get("home_power_target", 0.0))
    saved_power_units = st.session_state.get("home_power_units", "W")
    if saved_power_units not in unit_options:
        saved_power_units = "W"
    default_power_unit_index = unit_options.index(saved_power_units)

    # Budget scenario inputs
    saved_budget = float(st.session_state.get("home_budget", 0.0))
    saved_budget_basis = st.session_state.get("home_budget_basis", "Materials")

    # -----------------------------------------------------------
    # TOP SECTION: Design visual + key selectors & metrics
    # -----------------------------------------------------------
    top_left, top_right = st.columns([3, 2])

    with top_right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Array selection</div>', unsafe_allow_html=True)

        sel_name = st.selectbox(
            "Array design",
            design_names,
            index=default_design_index,
        )
        st.session_state["selected_array_design"] = sel_name

        design = next(d for d in designs if d["name"] == sel_name)
        num_cells = int(design.get("num_cells", 0))

        illumination = st.radio(
            "Illumination",
            illum_options,
            index=default_illum_index,
            horizontal=True,
        )
        st.session_state["selected_illumination"] = illumination

        power = compute_power_for_design(design)
        if illumination == "AM1.5":
            array_power = power["P_array_AM15_W"]
            icon = "☀️"
        else:
            array_power = power["P_array_AM0_W"]
            icon = "⚡"

        col_summary1, col_summary2 = st.columns(2)
        with col_summary1:
            st.metric(
                "Number of cells",
                f"{num_cells}",
            )
        with col_summary2:
            st.metric(
                f"Array power ({illumination})",
                f"{array_power:.2f} W",
            )
            st.caption(f"{icon} Based on {illumination} conditions")
        st.markdown("</div>", unsafe_allow_html=True)

    with top_left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title">String layout preview</div>',
            unsafe_allow_html=True,
        )
        _render_design_image(design)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # -----------------------------------------------------------
    # COST & LABOUR SNAPSHOT
    # -----------------------------------------------------------
    st.subheader("Cost & Labour Snapshot")

    materials_cost_per_array = st.session_state.get("materials_cost_per_array", None)

    # Labour per array
    labour_time_per_array_s, labour_cost_per_array = _compute_labour_per_array(num_cells)
    st.session_state["labour_time_per_array_s"] = labour_time_per_array_s
    st.session_state["labour_cost_per_array"] = labour_cost_per_array

    snapshot_col1, snapshot_col2, snapshot_col3 = st.columns(3)

    with snapshot_col1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Materials cost</div>', unsafe_allow_html=True)
        if materials_cost_per_array is None:
            st.info(
                "Materials cost per array not found. "
                "Visit the **Cost Summary** page to calculate it."
            )
        else:
            st.metric(
                "Materials cost per array",
                f"£{materials_cost_per_array:,.2f}",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with snapshot_col2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Labour per array</div>', unsafe_allow_html=True)
        if labour_time_per_array_s <= 0:
            st.info(
                "No cell/array-level labour timings defined yet on the "
                "**Labour** page, or no operators assigned."
            )
        else:
            labour_time_per_array_min = labour_time_per_array_s / 60.0
            st.metric(
                "Labour time per array",
                f"{labour_time_per_array_min:.2f} min",
            )
            st.metric(
                "Labour cost per array",
                f"£{labour_cost_per_array:,.2f}",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with snapshot_col3:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Labour per watt</div>', unsafe_allow_html=True)
        if labour_time_per_array_s > 0 and array_power > 0:
            time_per_watt_min = (labour_time_per_array_s / 60.0) / array_power
            cost_per_watt = labour_cost_per_array / array_power
            st.metric(
                "Time per W",
                f"{time_per_watt_min:.2f} min/W",
            )
            st.metric(
                "Cost per W",
                f"£{cost_per_watt:.2f} /W",
            )
            st.caption("Multiply by 1000 for £/kW.")
        else:
            st.info("Define labour timings and ensure array power > 0 to see these.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # -----------------------------------------------------------
    # CUSTOMER ORDER SCENARIOS
    # -----------------------------------------------------------
    st.subheader("Customer Order Scenarios")

    # Overall yield slider
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">Overall line yield</div>',
        unsafe_allow_html=True,
    )
    yield_frac = st.slider(
        "Fraction of built arrays that pass final test",
        min_value=0.50,
        max_value=1.00,
        value=float(saved_yield),
        step=0.01,
    )
    st.session_state["home_yield"] = yield_frac

    st.caption(
        "Example: 0.80 means only 80% of built arrays pass final test; "
        "scrap cost is implicitly included in the effective cost per good array."
    )
    st.markdown("</div>", unsafe_allow_html=True)

    tab_power, tab_budget = st.tabs(["By Power Requirement", "By Customer Budget"])

    # -----------------------------------------------------------
    # Scenario 1: Power required
    # -----------------------------------------------------------
    with tab_power:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title">Input – power requirement</div>',
            unsafe_allow_html=True,
        )

        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            target_power = st.number_input(
                "Target power required by customer",
                min_value=0.0,
                value=saved_target_power,
                step=10.0,
            )

        with col_t2:
            power_units = st.selectbox(
                "Units",
                unit_options,
                index=default_power_unit_index,
            )

        st.session_state["home_power_target"] = target_power
        st.session_state["home_power_units"] = power_units

        target_power_watts = (
            target_power * 1000.0 if power_units == "kW" else target_power
        )

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Result</div>', unsafe_allow_html=True)

        arrays_to_build = 0
        arrays_required_good = 0
        expected_scrap = 0

        if array_power <= 0 or target_power_watts <= 0:
            st.info("Enter a target power to calculate required arrays.")
        else:
            # Good arrays required to hit the power
            arrays_required_good = ceil(target_power_watts / array_power)

            if yield_frac > 0:
                arrays_to_build = ceil(arrays_required_good / yield_frac)
            else:
                arrays_to_build = arrays_required_good

            expected_scrap = max(arrays_to_build - arrays_required_good, 0)

            col_a1, col_a2, col_a3 = st.columns(3)
            with col_a1:
                st.metric(
                    "Good arrays required",
                    f"{arrays_required_good}",
                )
            with col_a2:
                st.metric(
                    "Arrays to build (incl. scrap)",
                    f"{arrays_to_build}",
                )
            with col_a3:
                st.metric(
                    "Expected scrap arrays",
                    f"{expected_scrap}",
                )

            if materials_cost_per_array is not None and materials_cost_per_array > 0:
                total_materials_cost = arrays_to_build * materials_cost_per_array
                effective_cost_per_good = (
                    total_materials_cost / arrays_required_good
                    if arrays_required_good > 0
                    else 0.0
                )

                st.markdown("##### Cost impact")

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.metric(
                        "Total materials cost for order",
                        f"£{total_materials_cost:,.2f}",
                    )
                with col_c2:
                    st.metric(
                        "Effective materials cost per good array",
                        f"£{effective_cost_per_good:,.2f}",
                    )
            else:
                st.info(
                    "Materials cost per array is not available, so cost metrics "
                    "cannot be calculated here."
                )

            # Labour impact for this scenario
            if arrays_to_build > 0 and labour_time_per_array_s > 0:
                st.markdown("##### Labour impact")

                total_labour_time_h = (
                    labour_time_per_array_s * arrays_to_build / 3600.0
                )
                total_labour_cost = labour_cost_per_array * arrays_to_build

                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    st.metric(
                        "Total labour time for order",
                        f"{total_labour_time_h:.2f} h",
                    )
                with col_l2:
                    st.metric(
                        "Total labour cost for order",
                        f"£{total_labour_cost:,.2f}",
                    )

        st.markdown("</div>", unsafe_allow_html=True)

        # Collapsible material requirements for this scenario
        if arrays_to_build > 0:
            _render_material_requirements_expander(
                "Material requirements for this scenario",
                arrays_to_build=arrays_to_build,
                design=design,
                materials=materials,
            )

    # -----------------------------------------------------------
    # Scenario 2: Customer budget (Materials vs Materials+Labour)
    # -----------------------------------------------------------
    with tab_budget:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title">Input – customer budget</div>',
            unsafe_allow_html=True,
        )

        budget = st.number_input(
            "Customer budget (£)",
            min_value=0.0,
            value=saved_budget,
            step=100.0,
        )
        st.session_state["home_budget"] = budget

        # NEW: choose whether budget covers materials only or materials + labour
        budget_basis = st.radio(
            "Budget covers:",
            ("Materials", "Materials + Labour"),
            index=0 if saved_budget_basis == "Materials" else 1,
            horizontal=True,
        )
        st.session_state["home_budget_basis"] = budget_basis

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Result</div>', unsafe_allow_html=True)

        arrays_we_can_build = 0
        good_arrays_expected = 0
        total_power_watts = 0.0
        total_power_kW = 0.0

        if materials_cost_per_array is None or materials_cost_per_array <= 0:
            st.info(
                "Materials cost per array is not available. "
                "Visit the **Cost Summary** page to compute it first."
            )
        elif budget <= 0:
            st.info("Enter a positive budget to estimate what can be delivered.")
        else:
            # Decide which cost per array to use based on selection
            if budget_basis == "Materials":
                cost_per_array_for_budget = materials_cost_per_array
            else:
                if labour_cost_per_array <= 0:
                    st.info(
                        "Labour cost per array is not available. "
                        "Update labour timings before using 'Materials + Labour'."
                    )
                    cost_per_array_for_budget = None
                else:
                    cost_per_array_for_budget = materials_cost_per_array + labour_cost_per_array

            if cost_per_array_for_budget is not None and cost_per_array_for_budget > 0:
                # How many arrays can we afford to build at all?
                arrays_we_can_build = int(budget // cost_per_array_for_budget)

                # Expected good arrays given yield
                good_arrays_expected = int(arrays_we_can_build * yield_frac)

                total_power_watts = good_arrays_expected * array_power
                total_power_kW = total_power_watts / 1000.0

                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    label = (
                        "Arrays we can afford to build (materials only)"
                        if budget_basis == "Materials"
                        else "Arrays we can afford to build (materials + labour)"
                    )
                    st.metric(label, f"{arrays_we_can_build}")
                with col_b2:
                    st.metric(
                        "Expected good arrays",
                        f"{good_arrays_expected}",
                    )
                with col_b3:
                    st.metric(
                        f"Estimated power ({illumination})",
                        f"{total_power_kW:.2f} kW",
                        help=f"{total_power_watts:.0f} W",
                    )

                if arrays_we_can_build == 0:
                    st.warning(
                        "Budget is too low to build even a single array at the "
                        f"current {budget_basis.lower()} cost."
                    )

                # Labour impact for this scenario
                if arrays_we_can_build > 0 and labour_time_per_array_s > 0:
                    st.markdown("##### Labour impact")

                    total_labour_time_h = (
                        labour_time_per_array_s * arrays_we_can_build / 3600.0
                    )
                    total_labour_cost = labour_cost_per_array * arrays_we_can_build

                    col_lb1, col_lb2 = st.columns(2)
                    with col_lb1:
                        st.metric(
                            "Total labour time for order",
                            f"{total_labour_time_h:.2f} h",
                        )
                    with col_lb2:
                        st.metric(
                            "Total labour cost for order",
                            f"£{total_labour_cost:,.2f}",
                        )

        st.markdown("</div>", unsafe_allow_html=True)

        # Collapsible material requirements for this scenario
        if arrays_we_can_build > 0:
            _render_material_requirements_expander(
                f"Material requirements for this scenario ({budget_basis})",
                arrays_to_build=arrays_we_can_build,
                design=design,
                materials=materials,
            )
