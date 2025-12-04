import streamlit as st

from model import load_materials, save_materials, load_product, MaterialItem


def _get_unit_price_gbp(item: MaterialItem, exchange_rate_gbp_per_usd: float) -> float:
    """
    For simple unit-priced items (frames, shipping boards, boxes):
    Convert stored unit price (USD or GBP) into GBP.
    """
    currency = (item.get("currency", "USD") or "USD").upper()
    try:
        if currency == "USD":
            unit_cost_usd = item.get("unit_cost_usd", None)
            if unit_cost_usd is None:
                return 0.0
            return float(unit_cost_usd) * float(exchange_rate_gbp_per_usd)
        else:
            unit_cost_gbp = item.get("unit_cost_gbp", None)
            if unit_cost_gbp is None:
                return 0.0
            return float(unit_cost_gbp)
    except (TypeError, ValueError):
        return 0.0


def _get_foam_cost_per_piece_gbp(
    item: MaterialItem, exchange_rate_gbp_per_usd: float
) -> float:
    """
    For anti-static foam:
    total_cost (USD/GBP) / number of pieces → £ per piece.
    """
    try:
        num_pieces = float(item.get("num_pieces", 0))
    except (TypeError, ValueError):
        return 0.0

    if num_pieces <= 0:
        return 0.0

    currency = (item.get("currency", "USD") or "USD").upper()

    try:
        if currency == "USD":
            total_cost_usd = item.get("total_cost_usd", None)
            if total_cost_usd is None:
                return 0.0
            total_cost_gbp = float(total_cost_usd) * float(exchange_rate_gbp_per_usd)
        else:
            total_cost_gbp = float(item.get("total_cost_gbp", 0.0))
    except (TypeError, ValueError):
        return 0.0

    if total_cost_gbp <= 0:
        return 0.0

    return total_cost_gbp / num_pieces


def render() -> None:
    """Packaging materials page."""
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    st.title("Packaging Materials")

    st.markdown(
        f"""
        Current exchange rate (GBP per USD): **{exchange_rate:.2f}**

        Packaging types handled here:

        1. **Frames** – unit price (USD/GBP) → used per array  
        2. **Shipping boards** – unit price (USD/GBP)  
        3. **Anti-static foam** – thickness + number of pieces + total cost → £/piece  
        4. **Shipping boxes** – diameter + unit price (USD/GBP) → £/box
        """
    )

    materials_db = load_materials()
    packaging_items = materials_db.get("Packaging", [])

    # ------------------ TABLE DISPLAY ------------------
    st.markdown("### Current Packaging items")

    if packaging_items:
        rows = []
        for item in packaging_items:
            row = dict(item)
            p_type = item.get("type", "Unknown")

            if p_type in ("Frame", "Shipping board", "Box"):
                unit_gbp = _get_unit_price_gbp(item, exchange_rate)
                if p_type == "Frame":
                    row["derived_cost"] = f"{unit_gbp:.2f} £/frame" if unit_gbp > 0 else "-"
                elif p_type == "Shipping board":
                    row["derived_cost"] = f"{unit_gbp:.2f} £/board" if unit_gbp > 0 else "-"
                else:  # Box
                    row["derived_cost"] = f"{unit_gbp:.2f} £/box" if unit_gbp > 0 else "-"
            elif p_type == "Foam":
                cp = _get_foam_cost_per_piece_gbp(item, exchange_rate)
                row["derived_cost"] = f"{cp:.6f} £/piece" if cp > 0 else "-"
            else:
                row["derived_cost"] = "-"

            rows.append(row)

        st.table(rows)
    else:
        st.info("No packaging items yet. Add some below.")

    st.markdown("---")

    # =========================================================
    #   ADD NEW FRAME
    # =========================================================
    with st.expander("➕ Add new Frame", expanded=False):
        with st.form("add_frame_item"):
            new_id = st.text_input("ID / Code", key="frame_id")
            new_name = st.text_input("Name / Description", key="frame_name")

            col = st.columns(2)
            with col[0]:
                unit_price = st.number_input(
                    "Unit price",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="frame_unit_price",
                )
            with col[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                    key="frame_currency",
                )

            notes = st.text_area(
                "Notes (optional)",
                value="",
                key="frame_notes",
            )

            submitted = st.form_submit_button("Add Frame")

            if submitted:
                if not new_id.strip():
                    st.error("ID required.")
                elif not new_name.strip():
                    st.error("Name required.")
                elif unit_price <= 0:
                    st.error("Unit price must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "type": "Frame",
                        "currency": currency,
                    }

                    if currency == "USD":
                        item["unit_cost_usd"] = float(unit_price)
                    else:
                        item["unit_cost_gbp"] = float(unit_price)

                    if notes.strip():
                        item["notes"] = notes.strip()

                    packaging_items.append(item)
                    materials_db["Packaging"] = packaging_items
                    save_materials(materials_db)

                    st.success("Frame item added ✅")
                    st.rerun()

    st.markdown("---")

    # =========================================================
    #   ADD NEW SHIPPING BOARD
    # =========================================================
    with st.expander("➕ Add new Shipping board", expanded=False):
        with st.form("add_board_item"):
            new_id = st.text_input("ID / Code", key="board_id")
            new_name = st.text_input("Name / Description", key="board_name")

            col = st.columns(2)
            with col[0]:
                unit_price = st.number_input(
                    "Unit price",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="board_unit_price",
                )
            with col[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                    key="board_currency",
                )

            notes = st.text_area(
                "Notes (optional)",
                value="",
                key="board_notes",
            )

            submitted = st.form_submit_button("Add Shipping board")

            if submitted:
                if not new_id.strip():
                    st.error("ID required.")
                elif not new_name.strip():
                    st.error("Name required.")
                elif unit_price <= 0:
                    st.error("Unit price must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "type": "Shipping board",
                        "currency": currency,
                    }

                    if currency == "USD":
                        item["unit_cost_usd"] = float(unit_price)
                    else:
                        item["unit_cost_gbp"] = float(unit_price)

                    if notes.strip():
                        item["notes"] = notes.strip()

                    packaging_items.append(item)
                    materials_db["Packaging"] = packaging_items
                    save_materials(materials_db)

                    st.success("Shipping board item added ✅")
                    st.rerun()

    st.markdown("---")

    # =========================================================
    #   ADD NEW ANTI-STATIC FOAM
    # =========================================================
    with st.expander("➕ Add new Anti-static foam", expanded=False):
        with st.form("add_foam_item"):
            new_id = st.text_input("ID / Code", key="foam_id")
            new_name = st.text_input("Name / Description", key="foam_name")

            thickness_mm = st.number_input(
                "Thickness (mm)",
                min_value=0.0,
                value=5.0,
                step=0.5,
                format="%.2f",
                key="foam_thickness_mm",
            )

            num_pieces = st.number_input(
                "Number of pieces",
                min_value=1,
                value=10,
                step=1,
                key="foam_num_pieces",
            )

            col = st.columns(2)
            with col[0]:
                total_cost = st.number_input(
                    "Total cost",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="foam_total_cost",
                )
            with col[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                    key="foam_currency",
                )

            notes = st.text_area(
                "Notes (optional)",
                value="",
                key="foam_notes",
            )

            submitted = st.form_submit_button("Add Foam item")

            if submitted:
                if not new_id.strip():
                    st.error("ID required.")
                elif not new_name.strip():
                    st.error("Name required.")
                elif thickness_mm <= 0:
                    st.error("Thickness must be > 0.")
                elif num_pieces <= 0:
                    st.error("Number of pieces must be > 0.")
                elif total_cost <= 0:
                    st.error("Total cost must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "type": "Foam",
                        "thickness_mm": float(thickness_mm),
                        "num_pieces": int(num_pieces),
                        "currency": currency,
                    }

                    if currency == "USD":
                        item["total_cost_usd"] = float(total_cost)
                    else:
                        item["total_cost_gbp"] = float(total_cost)

                    if notes.strip():
                        item["notes"] = notes.strip()

                    packaging_items.append(item)
                    materials_db["Packaging"] = packaging_items
                    save_materials(materials_db)

                    st.success("Foam item added ✅")
                    st.rerun()

    st.markdown("---")

    # =========================================================
    #   ADD NEW SHIPPING BOX
    # =========================================================
    with st.expander("➕ Add new Shipping box", expanded=False):
        with st.form("add_box_item"):
            new_id = st.text_input("ID / Code", key="box_id")
            new_name = st.text_input("Name / Description", key="box_name")

            diameter_mm = st.number_input(
                "Diameter (mm)",
                min_value=0.0,
                value=200.0,
                step=5.0,
                format="%.1f",
                key="box_diameter_mm",
            )

            col = st.columns(2)
            with col[0]:
                unit_price = st.number_input(
                    "Unit price",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="box_unit_price",
                )
            with col[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                    key="box_currency",
                )

            notes = st.text_area(
                "Notes (optional)",
                value="",
                key="box_notes",
            )

            submitted = st.form_submit_button("Add Box item")

            if submitted:
                if not new_id.strip():
                    st.error("ID required.")
                elif not new_name.strip():
                    st.error("Name required.")
                elif diameter_mm <= 0:
                    st.error("Diameter must be > 0.")
                elif unit_price <= 0:
                    st.error("Unit price must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "type": "Box",
                        "diameter_mm": float(diameter_mm),
                        "currency": currency,
                    }

                    if currency == "USD":
                        item["unit_cost_usd"] = float(unit_price)
                    else:
                        item["unit_cost_gbp"] = float(unit_price)

                    if notes.strip():
                        item["notes"] = notes.strip()

                    packaging_items.append(item)
                    materials_db["Packaging"] = packaging_items
                    save_materials(materials_db)

                    st.success("Box item added ✅")
                    st.rerun()

    st.markdown("---")

    # =========================================================
    #   DELETE PACKAGING ITEM
    # =========================================================
    if packaging_items:
        with st.expander("🗑️ Delete Packaging item", expanded=False):
            labels = [
                f"{i}: {item.get('type', '?')} – {item.get('id')} – {item.get('name')}"
                for i, item in enumerate(packaging_items)
            ]
            sel = st.selectbox("Select item to delete", labels)

            idx = int(sel.split(":", 1)[0])

            if st.button("Delete selected Packaging item"):
                removed = packaging_items.pop(idx)
                materials_db["Packaging"] = packaging_items
                save_materials(materials_db)

                st.warning(
                    f"Deleted {removed.get('type', '?')} – {removed.get('id')}"
                )
                st.rerun()
