import streamlit as st

from model import (
    load_array_designs,
    save_array_designs,
    load_materials,
    ArrayDesign,
)

# Assumptions for power calculations
CELL_AREA_CM2 = 20.0
CELL_AREA_M2 = CELL_AREA_CM2 / 10_000.0  # 20 cm^2 -> 0.002 m^2
IRRADIANCE_AM15 = 1000.0  # W/m^2 (typical lab AM1.5G)
IRRADIANCE_AM0 = 1366.0   # W/m^2 (approx solar constant)


def compute_power_for_design(design: ArrayDesign) -> dict:
    """
    Compute power per cell and per array at AM1.5 and AM0.
    """
    num_cells = float(design.get("num_cells", 0))
    eff15_pct = float(design.get("eff_am15_percent", 0.0))
    eff0_pct = float(design.get("eff_am0_percent", 0.0))

    eff15 = eff15_pct / 100.0
    eff0 = eff0_pct / 100.0

    p_cell_15 = eff15 * IRRADIANCE_AM15 * CELL_AREA_M2
    p_array_15 = p_cell_15 * num_cells

    p_cell_0 = eff0 * IRRADIANCE_AM0 * CELL_AREA_M2
    p_array_0 = p_cell_0 * num_cells

    return {
        "P_cell_AM15_W": p_cell_15,
        "P_array_AM15_W": p_array_15,
        "P_cell_AM0_W": p_cell_0,
        "P_array_AM0_W": p_array_0,
    }


def _silver_labels(silver_items):
    """Helper to build dropdown labels for Silver Ribbon items."""
    return [
        f"{i}: {item.get('id', '(no id)')} – "
        f"{item.get('name', '(no name)')} "
        f"({item.get('width_mm', '?')} mm)"
        for i, item in enumerate(silver_items)
    ]


def _find_silver_index_by_id(silver_items, silver_id: str) -> int:
    """Find index in silver_items with given id, default to 0 if not found."""
    if not silver_items:
        return 0
    for i, item in enumerate(silver_items):
        if str(item.get("id", "")) == str(silver_id):
            return i
    return 0


def render() -> None:
    st.title("Array Designs")

    st.markdown(
        """
        Define different array designs here. Each design specifies:

        1. **Number of cells**  
        2. **Cell efficiency at AM1.5 and AM0** (20 cm² cells → power per cell and per array)  
        3. **Cell height and gaps**  
        4. **End gaps**  
        5. **Blocking diode tabs** – *lengths + Silver Ribbon width*  
        6. **Negative end bars** – *Silver width + length*  
        7. **Negative bars** – *Silver width + length*
        """
    )

    designs = load_array_designs()
    materials_db = load_materials()
    silver_items = materials_db.get("Silver Ribbon", [])

    # ------------------ SHOW EXISTING DESIGNS ------------------
    st.markdown("### Existing Array Designs")

    if designs:
        rows = []
        for d in designs:
            row = dict(d)
            row.update(compute_power_for_design(d))
            rows.append(row)
        st.table(rows)
    else:
        st.info("No designs yet. Add one below.")

    st.markdown("---")

    # =========================================================
    #   ADD NEW DESIGN
    # =========================================================
    with st.expander("➕ Add new Array Design", expanded=False):
        with st.form("add_design"):
            name = st.text_input("Design name", key="add_name")

            col_cells = st.columns(3)
            with col_cells[0]:
                num_cells = st.number_input(
                    "No. cells",
                    min_value=1,
                    value=20,
                    step=1,
                    key="add_num_cells",
                )
            with col_cells[1]:
                eff15 = st.number_input(
                    "Efficiency AM1.5 (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=30.0,
                    step=0.1,
                    format="%.2f",
                    key="add_eff15",
                )
            with col_cells[2]:
                eff0 = st.number_input(
                    "Efficiency AM0 (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=31.0,
                    step=0.1,
                    format="%.2f",
                    key="add_eff0",
                )

            # Geometry
            st.markdown("#### Geometry (mm)")
            col_geom = st.columns(4)
            with col_geom[0]:
                cell_height = st.number_input(
                    "Cell height (mm)",
                    min_value=0.0,
                    value=6.6,
                    step=0.1,
                    format="%.2f",
                    key="add_cell_height",
                )
            with col_geom[1]:
                gap = st.number_input(
                    "Gap between cells (mm)",
                    min_value=0.0,
                    value=1.0,
                    step=0.1,
                    format="%.2f",
                    key="add_gap",
                )
            with col_geom[2]:
                pos_gap = st.number_input(
                    "Positive end gap (mm)",
                    min_value=0.0,
                    value=5.0,
                    step=0.1,
                    format="%.2f",
                    key="add_pos_gap",
                )
            with col_geom[3]:
                neg_gap = st.number_input(
                    "Negative end gap (mm)",
                    min_value=0.0,
                    value=5.0,
                    step=0.1,
                    format="%.2f",
                    key="add_neg_gap",
                )

            # Blocking diode tabs
            st.markdown("#### Blocking Diode Tabs")

            if not silver_items:
                st.error(
                    "No Silver Ribbon materials found. "
                    "Please add at least one Silver Ribbon item first."
                )
                submitted = st.form_submit_button("Add Array Design")
                if submitted:
                    st.stop()
            else:
                labels = _silver_labels(silver_items)
                sel_block = st.selectbox(
                    "Blocking diode tab width (Silver Ribbon)",
                    labels,
                    index=0,
                    key="add_block_silver",
                )
                block_idx = int(sel_block.split(":", 1)[0])
                block_item = silver_items[block_idx]

            col_tabs = st.columns(2)
            with col_tabs[0]:
                block_len1 = st.number_input(
                    "Tab length 1 (mm)",
                    min_value=0.0,
                    value=10.0,
                    step=0.5,
                    format="%.2f",
                    key="add_block_len1",
                )
            with col_tabs[1]:
                block_len2 = st.number_input(
                    "Tab length 2 (mm)",
                    min_value=0.0,
                    value=10.0,
                    step=0.5,
                    format="%.2f",
                    key="add_block_len2",
                )

            # Negative end bar
            st.markdown("#### Negative End Bar")
            sel_neg_end = st.selectbox(
                "Negative end width (Silver Ribbon)",
                labels,
                index=0,
                key="add_neg_end_silver",
            )
            neg_end_idx = int(sel_neg_end.split(":", 1)[0])
            neg_end_item = silver_items[neg_end_idx]

            neg_end_len = st.number_input(
                "Negative end length (mm) (doubled later – two bars)",
                min_value=0.0,
                value=20.0,
                step=0.5,
                format="%.2f",
                key="add_neg_end_len",
            )

            # Negative bar
            st.markdown("#### Negative Bar")
            sel_neg_bar = st.selectbox(
                "Negative bar width (Silver Ribbon)",
                labels,
                index=0,
                key="add_neg_bar_silver",
            )
            neg_bar_idx = int(sel_neg_bar.split(":", 1)[0])
            neg_bar_item = silver_items[neg_bar_idx]

            neg_bar_len = st.number_input(
                "Negative bar length (mm)",
                min_value=0.0,
                value=30.0,
                step=0.5,
                format="%.2f",
                key="add_neg_bar_len",
            )

            submitted = st.form_submit_button("Add Array Design")

            if submitted:
                if not name.strip():
                    st.error("Please enter a design name.")
                else:
                    new_design: ArrayDesign = {
                        "name": name.strip(),
                        "num_cells": int(num_cells),
                        "eff_am15_percent": float(eff15),
                        "eff_am0_percent": float(eff0),
                        "cell_height_mm": float(cell_height),
                        "gap_between_cells_mm": float(gap),
                        "positive_end_gap_mm": float(pos_gap),
                        "negative_end_gap_mm": float(neg_gap),
                        "blocking_tab_silver_id": block_item.get("id", ""),
                        "blocking_tab_width_mm": float(block_item.get("width_mm", 0.0)),
                        "blocking_tab_length1_mm": float(block_len1),
                        "blocking_tab_length2_mm": float(block_len2),
                        "negative_end_silver_id": neg_end_item.get("id", ""),
                        "negative_end_width_mm": float(
                            neg_end_item.get("width_mm", 0.0)
                        ),
                        "negative_end_length_mm": float(neg_end_len),
                        "negative_bar_silver_id": neg_bar_item.get("id", ""),
                        "negative_bar_width_mm": float(
                            neg_bar_item.get("width_mm", 0.0)
                        ),
                        "negative_bar_length_mm": float(neg_bar_len),
                    }

                    designs.append(new_design)
                    save_array_designs(designs)
                    st.success("Array design added successfully ✅")
                    st.rerun()

    # =========================================================
    #   EDIT EXISTING DESIGN
    # =========================================================
    if designs:
        st.markdown("---")
        with st.expander("✏️ Edit existing Array Design", expanded=False):
            labels_designs = [
                f"{i}: {d.get('name', '(no name)')} – {d.get('num_cells', '?')} cells"
                for i, d in enumerate(designs)
            ]
            sel_design = st.selectbox(
                "Select design to edit",
                labels_designs,
                key="edit_select_design",
            )
            edit_idx = int(sel_design.split(":", 1)[0])
            design = designs[edit_idx]

            with st.form("edit_design_form"):
                name = st.text_input(
                    "Design name",
                    value=design.get("name", ""),
                    key="edit_name",
                )

                col_cells = st.columns(3)
                with col_cells[0]:
                    num_cells = st.number_input(
                        "No. cells",
                        min_value=1,
                        value=int(design.get("num_cells", 1)),
                        step=1,
                        key="edit_num_cells",
                    )
                with col_cells[1]:
                    eff15 = st.number_input(
                        "Efficiency AM1.5 (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(design.get("eff_am15_percent", 0.0)),
                        step=0.1,
                        format="%.2f",
                        key="edit_eff15",
                    )
                with col_cells[2]:
                    eff0 = st.number_input(
                        "Efficiency AM0 (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(design.get("eff_am0_percent", 0.0)),
                        step=0.1,
                        format="%.2f",
                        key="edit_eff0",
                    )

                # Geometry
                st.markdown("#### Geometry (mm)")
                col_geom = st.columns(4)
                with col_geom[0]:
                    cell_height = st.number_input(
                        "Cell height (mm)",
                        min_value=0.0,
                        value=float(design.get("cell_height_mm", 0.0)),
                        step=0.1,
                        format="%.2f",
                        key="edit_cell_height",
                    )
                with col_geom[1]:
                    gap = st.number_input(
                        "Gap between cells (mm)",
                        min_value=0.0,
                        value=float(design.get("gap_between_cells_mm", 0.0)),
                        step=0.1,
                        format="%.2f",
                        key="edit_gap",
                    )
                with col_geom[2]:
                    pos_gap = st.number_input(
                        "Positive end gap (mm)",
                        min_value=0.0,
                        value=float(design.get("positive_end_gap_mm", 0.0)),
                        step=0.1,
                        format="%.2f",
                        key="edit_pos_gap",
                    )
                with col_geom[3]:
                    neg_gap = st.number_input(
                        "Negative end gap (mm)",
                        min_value=0.0,
                        value=float(design.get("negative_end_gap_mm", 0.0)),
                        step=0.1,
                        format="%.2f",
                        key="edit_neg_gap",
                    )

                # Blocking tabs
                st.markdown("#### Blocking Diode Tabs")

                if not silver_items:
                    st.error(
                        "No Silver Ribbon materials found. "
                        "Please add at least one Silver Ribbon item first."
                    )
                    save_changes = st.form_submit_button("Save changes")
                    if save_changes:
                        st.stop()
                else:
                    labels = _silver_labels(silver_items)
                    prev_block_id = design.get("blocking_tab_silver_id", "")
                    default_block_idx = _find_silver_index_by_id(
                        silver_items, prev_block_id
                    )
                    sel_block = st.selectbox(
                        "Blocking diode tab width (Silver Ribbon)",
                        labels,
                        index=default_block_idx,
                        key="edit_block_silver",
                    )
                    block_idx = int(sel_block.split(":", 1)[0])
                    block_item = silver_items[block_idx]

                col_tabs = st.columns(2)
                with col_tabs[0]:
                    block_len1 = st.number_input(
                        "Tab length 1 (mm)",
                        min_value=0.0,
                        value=float(design.get("blocking_tab_length1_mm", 0.0)),
                        step=0.5,
                        format="%.2f",
                        key="edit_block_len1",
                    )
                with col_tabs[1]:
                    block_len2 = st.number_input(
                        "Tab length 2 (mm)",
                        min_value=0.0,
                        value=float(design.get("blocking_tab_length2_mm", 0.0)),
                        step=0.5,
                        format="%.2f",
                        key="edit_block_len2",
                    )

                # Negative end bar
                st.markdown("#### Negative End Bar")
                prev_neg_end_id = design.get("negative_end_silver_id", "")
                default_neg_end_idx = _find_silver_index_by_id(
                    silver_items, prev_neg_end_id
                )
                sel_neg_end = st.selectbox(
                    "Negative end width (Silver Ribbon)",
                    labels,
                    index=default_neg_end_idx,
                    key="edit_neg_end_silver",
                )
                neg_end_idx = int(sel_neg_end.split(":", 1)[0])
                neg_end_item = silver_items[neg_end_idx]

                neg_end_len = st.number_input(
                    "Negative end length (mm) (doubled later – two bars)",
                    min_value=0.0,
                    value=float(design.get("negative_end_length_mm", 0.0)),
                    step=0.5,
                    format="%.2f",
                    key="edit_neg_end_len",
                )

                # Negative bar
                st.markdown("#### Negative Bar")
                prev_neg_bar_id = design.get("negative_bar_silver_id", "")
                default_neg_bar_idx = _find_silver_index_by_id(
                    silver_items, prev_neg_bar_id
                )
                sel_neg_bar = st.selectbox(
                    "Negative bar width (Silver Ribbon)",
                    labels,
                    index=default_neg_bar_idx,
                    key="edit_neg_bar_silver",
                )
                neg_bar_idx = int(sel_neg_bar.split(":", 1)[0])
                neg_bar_item = silver_items[neg_bar_idx]

                neg_bar_len = st.number_input(
                    "Negative bar length (mm)",
                    min_value=0.0,
                    value=float(design.get("negative_bar_length_mm", 0.0)),
                    step=0.5,
                    format="%.2f",
                    key="edit_neg_bar_len",
                )

                save_changes = st.form_submit_button("Save changes")

                if save_changes:
                    if not name.strip():
                        st.error("Please enter a design name.")
                    else:
                        design["name"] = name.strip()
                        design["num_cells"] = int(num_cells)
                        design["eff_am15_percent"] = float(eff15)
                        design["eff_am0_percent"] = float(eff0)
                        design["cell_height_mm"] = float(cell_height)
                        design["gap_between_cells_mm"] = float(gap)
                        design["positive_end_gap_mm"] = float(pos_gap)
                        design["negative_end_gap_mm"] = float(neg_gap)
                        design["blocking_tab_silver_id"] = block_item.get("id", "")
                        design["blocking_tab_width_mm"] = float(
                            block_item.get("width_mm", 0.0)
                        )
                        design["blocking_tab_length1_mm"] = float(block_len1)
                        design["blocking_tab_length2_mm"] = float(block_len2)
                        design["negative_end_silver_id"] = neg_end_item.get("id", "")
                        design["negative_end_width_mm"] = float(
                            neg_end_item.get("width_mm", 0.0)
                        )
                        design["negative_end_length_mm"] = float(neg_end_len)
                        design["negative_bar_silver_id"] = neg_bar_item.get("id", "")
                        design["negative_bar_width_mm"] = float(
                            neg_bar_item.get("width_mm", 0.0)
                        )
                        design["negative_bar_length_mm"] = float(neg_bar_len)

                        designs[edit_idx] = design
                        save_array_designs(designs)
                        st.success("Array design updated ✅")
                        st.rerun()

    # =========================================================
    #   DELETE DESIGN
    # =========================================================
    if designs:
        st.markdown("---")
        with st.expander("🗑️ Delete Array Design", expanded=False):
            labels_designs = [
                f"{i}: {d.get('name', '(no name)')} – {d.get('num_cells', '?')} cells"
                for i, d in enumerate(designs)
            ]
            sel_design = st.selectbox(
                "Select design to delete",
                labels_designs,
                key="delete_select_design",
            )
            del_idx = int(sel_design.split(":", 1)[0])

            if st.button("Delete selected design"):
                removed = designs.pop(del_idx)
                save_array_designs(designs)
                st.warning(
                    f"Deleted design: {removed.get('name', '(no name)')}"
                )
                st.rerun()
