import streamlit as st

from model import load_materials, save_materials, load_product, MaterialItem


FT_TO_M = 0.3048


def compute_cost_per_m_gbp(item: MaterialItem, exchange_rate_gbp_per_usd: float) -> float:
    """
    Compute derived cost per metre in GBP for a lamination roll.

    Uses:
    - roll_length_value
    - roll_length_unit ("m" or "ft")
    - roll_cost_usd / roll_cost_gbp
    - roll_currency ("USD" or "GBP")

    cost_per_m_gbp = roll_cost_in_GBP / roll_length_in_m
    """
    try:
        length_value = float(item.get("roll_length_value", 0.0))
    except (TypeError, ValueError):
        return 0.0

    if length_value <= 0:
        return 0.0

    unit = (item.get("roll_length_unit", "m") or "m").lower()
    currency = (item.get("roll_currency", "USD") or "USD").upper()

    # Convert length to metres
    if unit == "ft":
        length_m = length_value * FT_TO_M
    else:
        length_m = length_value

    if length_m <= 0:
        return 0.0

    # Get roll cost in GBP
    roll_cost_usd = item.get("roll_cost_usd", None)
    roll_cost_gbp = item.get("roll_cost_gbp", None)

    try:
        if currency == "USD":
            if roll_cost_usd is None:
                return 0.0
            cost_gbp = float(roll_cost_usd) * float(exchange_rate_gbp_per_usd)
        else:
            if roll_cost_gbp is None:
                return 0.0
            cost_gbp = float(roll_cost_gbp)
    except (TypeError, ValueError):
        return 0.0

    if cost_gbp <= 0:
        return 0.0

    return cost_gbp / length_m


def render() -> None:
    """CRUD page for Lamination rolls with £/m logic."""
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    st.title("Lamination Rolls")

    st.markdown(
        f"""
        Current exchange rate (GBP per USD): **{exchange_rate:.2f}**

        For each lamination material, you enter:
        - **Roll length** (in metres or feet)
        - **Roll cost** (quoted in USD or GBP)

        The app then derives **cost per metre in GBP**.
        """
    )

    materials_db = load_materials()
    laminations = materials_db.get("Lamination", [])

    # ------------------ LIST ITEMS ------------------
    st.markdown("### Current Lamination items")

    if laminations:
        rows = []
        for item in laminations:
            row = dict(item)
            cost_per_m_gbp = compute_cost_per_m_gbp(item, exchange_rate)
            row["cost_per_m_gbp (derived)"] = (
                f"{cost_per_m_gbp:.6f}" if cost_per_m_gbp > 0 else "-"
            )
            rows.append(row)

        st.table(rows)
    else:
        st.info("No lamination items yet. Add one below.")

    st.markdown("---")

    # ------------------ ADD NEW ITEM ------------------
    with st.expander("➕ Add new Lamination roll", expanded=False):
        with st.form("add_lamination_item"):
            new_id = st.text_input("ID / Code", value="")
            new_name = st.text_input("Name / Description", value="")

            col_len = st.columns(2)
            with col_len[0]:
                roll_length_value = st.number_input(
                    "Roll length",
                    min_value=0.0,
                    value=100.0,
                    step=1.0,
                    format="%.2f",
                )
            with col_len[1]:
                roll_length_unit = st.selectbox(
                    "Roll length unit",
                    ["m", "ft"],
                    index=0,
                )

            col_cost = st.columns(2)
            with col_cost[0]:
                roll_cost = st.number_input(
                    "Roll cost",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                )
            with col_cost[1]:
                roll_currency = st.selectbox(
                    "Roll currency",
                    ["USD", "GBP"],
                    index=0,
                )

            new_notes = st.text_area("Notes (optional)", value="")

            submitted = st.form_submit_button("Add lamination roll")

            if submitted:
                if not new_id.strip():
                    st.error("Please provide an ID / Code.")
                elif not new_name.strip():
                    st.error("Please provide a Name / Description.")
                elif roll_length_value <= 0:
                    st.error("Roll length must be > 0.")
                elif roll_cost <= 0:
                    st.error("Roll cost must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "roll_length_value": float(roll_length_value),
                        "roll_length_unit": roll_length_unit,
                        "roll_currency": roll_currency,
                    }

                    if roll_currency == "USD":
                        item["roll_cost_usd"] = float(roll_cost)
                    else:
                        item["roll_cost_gbp"] = float(roll_cost)

                    if new_notes.strip():
                        item["notes"] = new_notes.strip()

                    laminations.append(item)
                    materials_db["Lamination"] = laminations
                    save_materials(materials_db)

                    st.success("Lamination roll added and saved to materials.yaml ✅")
                    st.rerun()

    st.markdown("---")

    # ------------------ EDIT ITEM ------------------
    if laminations:
        with st.expander("✏️ Edit existing Lamination roll", expanded=False):
            labels = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(laminations)
            ]
            selected = st.selectbox("Select lamination to edit", labels)
            idx = int(selected.split(":", 1)[0])
            selected_item = laminations[idx]

            with st.form("edit_lamination_item"):
                edit_id = st.text_input(
                    "ID / Code",
                    value=selected_item.get("id", ""),
                )
                edit_name = st.text_input(
                    "Name / Description",
                    value=selected_item.get("name", ""),
                )

                # Length
                col_len_e = st.columns(2)
                with col_len_e[0]:
                    edit_roll_length_value = st.number_input(
                        "Roll length",
                        min_value=0.0,
                        value=float(selected_item.get("roll_length_value", 0.0)),
                        step=1.0,
                        format="%.2f",
                    )
                with col_len_e[1]:
                    current_len_unit = (
                        selected_item.get("roll_length_unit", "m") or "m"
                    ).lower()
                    edit_roll_length_unit = st.selectbox(
                        "Roll length unit",
                        ["m", "ft"],
                        index=0 if current_len_unit == "m" else 1,
                    )

                # Cost + currency
                current_currency = (
                    selected_item.get("roll_currency", "USD") or "USD"
                ).upper()
                if current_currency == "USD":
                    current_cost = float(selected_item.get("roll_cost_usd", 0.0))
                else:
                    current_cost = float(selected_item.get("roll_cost_gbp", 0.0))

                col_cost_e = st.columns(2)
                with col_cost_e[0]:
                    edit_roll_cost = st.number_input(
                        "Roll cost",
                        min_value=0.0,
                        value=current_cost,
                        step=0.01,
                        format="%.2f",
                    )
                with col_cost_e[1]:
                    edit_roll_currency = st.selectbox(
                        "Roll currency",
                        ["USD", "GBP"],
                        index=0 if current_currency == "USD" else 1,
                    )

                edit_notes = st.text_area(
                    "Notes (optional)",
                    value=selected_item.get("notes", ""),
                )

                save_changes = st.form_submit_button("Save changes")

                if save_changes:
                    if not edit_id.strip():
                        st.error("Please provide an ID / Code.")
                    elif not edit_name.strip():
                        st.error("Please provide a Name / Description.")
                    elif edit_roll_length_value <= 0:
                        st.error("Roll length must be > 0.")
                    elif edit_roll_cost <= 0:
                        st.error("Roll cost must be > 0.")
                    else:
                        selected_item["id"] = edit_id.strip()
                        selected_item["name"] = edit_name.strip()
                        selected_item["roll_length_value"] = float(
                            edit_roll_length_value
                        )
                        selected_item["roll_length_unit"] = edit_roll_length_unit
                        selected_item["roll_currency"] = edit_roll_currency

                        if edit_roll_currency == "USD":
                            selected_item["roll_cost_usd"] = float(edit_roll_cost)
                            selected_item.pop("roll_cost_gbp", None)
                        else:
                            selected_item["roll_cost_gbp"] = float(edit_roll_cost)
                            selected_item.pop("roll_cost_usd", None)

                        if edit_notes.strip():
                            selected_item["notes"] = edit_notes.strip()
                        else:
                            selected_item.pop("notes", None)

                        laminations[idx] = selected_item
                        materials_db["Lamination"] = laminations
                        save_materials(materials_db)

                        st.success("Lamination roll updated successfully ✅")
                        st.rerun()

    # ------------------ DELETE ITEM ------------------
    if laminations:
        st.markdown("---")
        with st.expander("🗑️ Delete Lamination roll", expanded=False):
            labels_del = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(laminations)
            ]
            selected_del = st.selectbox(
                "Select lamination to delete",
                labels_del,
                key="delete_lamination_select",
            )
            idx_del = int(selected_del.split(":", 1)[0])

            if st.button("Delete selected lamination"):
                removed = laminations.pop(idx_del)
                materials_db["Lamination"] = laminations
                save_materials(materials_db)

                st.warning(
                    f"Deleted: {removed.get('id', '(no id)')} – "
                    f"{removed.get('name', '(no name)')}"
                )
                st.rerun()
