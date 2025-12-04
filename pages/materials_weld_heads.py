import streamlit as st

from model import load_materials, save_materials, load_product, MaterialItem


def compute_cost_per_weld_gbp(item: MaterialItem, exchange_rate_gbp_per_usd: float) -> float:
    """
    Compute derived cost per weld in GBP.

    Uses:
    - unit_cost_usd / unit_cost_gbp
    - currency
    - num_welds

    cost_per_weld_gbp = (unit_price in GBP) / num_welds
    """
    try:
        num_welds = float(item.get("num_welds", 0))
    except (TypeError, ValueError):
        return 0.0

    if num_welds <= 0:
        return 0.0

    currency = (item.get("currency", "USD") or "USD").upper()

    # Get base price in its own currency
    unit_cost_usd = item.get("unit_cost_usd", None)
    unit_cost_gbp = item.get("unit_cost_gbp", None)

    try:
        if currency == "USD":
            if unit_cost_usd is None:
                return 0.0
            price_gbp = float(unit_cost_usd) * float(exchange_rate_gbp_per_usd)
        else:
            if unit_cost_gbp is None:
                return 0.0
            price_gbp = float(unit_cost_gbp)
    except (TypeError, ValueError):
        return 0.0

    if price_gbp <= 0:
        return 0.0

    return price_gbp / num_welds


def render() -> None:
    """CRUD page for Weld heads with cost per weld logic."""
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    st.title("Weld Heads")

    st.markdown(
        f"""
        Current exchange rate (GBP per USD): **{exchange_rate:.2f}**

        Each weld head has:
        - a **unit price** (in USD or GBP)
        - a **number of welds** it can perform

        The app derives **cost per weld in GBP** from these.
        """
    )

    materials_db = load_materials()
    weld_heads = materials_db.get("Weld heads", [])

    # ------------------ LIST ITEMS ------------------
    st.markdown("### Current Weld Head items")

    if weld_heads:
        rows = []
        for item in weld_heads:
            row = dict(item)  # copy for display
            cost_per_weld_gbp = compute_cost_per_weld_gbp(item, exchange_rate)
            row["cost_per_weld_gbp (derived)"] = (
                f"{cost_per_weld_gbp:.6f}" if cost_per_weld_gbp > 0 else "-"
            )
            rows.append(row)

        st.table(rows)
    else:
        st.info("No weld head items yet. Add one below.")

    st.markdown("---")

    # ------------------ ADD NEW ITEM ------------------
    with st.expander("➕ Add new Weld head", expanded=False):
        with st.form("add_weld_head_item"):
            new_id = st.text_input("ID / Code", value="")
            new_name = st.text_input("Name / Description", value="")

            col1 = st.columns(2)
            with col1[0]:
                unit_price = st.number_input(
                    "Unit price",
                    min_value=0.0,
                    value=0.0,
                    step=0.0001,
                    format="%.2f",
                )
            with col1[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                )

            num_welds = st.number_input(
                "No. welds (lifetime weld count for this head)",
                min_value=1,
                value=1000,
                step=1,
            )

            new_notes = st.text_area("Notes (optional)", value="")

            submitted = st.form_submit_button("Add weld head")

            if submitted:
                if not new_id.strip():
                    st.error("Please provide an ID / Code.")
                elif not new_name.strip():
                    st.error("Please provide a Name / Description.")
                elif unit_price <= 0:
                    st.error("Unit price must be > 0.")
                elif num_welds <= 0:
                    st.error("Number of welds must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "currency": currency,
                        "num_welds": int(num_welds),
                    }

                    # Store in the correct currency field
                    if currency == "USD":
                        item["unit_cost_usd"] = float(unit_price)
                    else:
                        item["unit_cost_gbp"] = float(unit_price)

                    if new_notes.strip():
                        item["notes"] = new_notes.strip()

                    weld_heads.append(item)
                    materials_db["Weld heads"] = weld_heads
                    save_materials(materials_db)

                    st.success("Weld head added and saved to materials.yaml ✅")
                    st.rerun()

    st.markdown("---")

    # ------------------ EDIT ITEM ------------------
    if weld_heads:
        with st.expander("✏️ Edit existing Weld head", expanded=False):
            labels = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(weld_heads)
            ]
            selected = st.selectbox("Select weld head to edit", labels)
            idx = int(selected.split(":", 1)[0])
            selected_item = weld_heads[idx]

            with st.form("edit_weld_head_item"):
                edit_id = st.text_input(
                    "ID / Code", value=selected_item.get("id", "")
                )
                edit_name = st.text_input(
                    "Name / Description", value=selected_item.get("name", "")
                )

                # Determine current price + currency
                current_currency = (selected_item.get("currency", "USD") or "USD").upper()
                if current_currency == "USD":
                    current_price = float(selected_item.get("unit_cost_usd", 0.0))
                else:
                    current_price = float(selected_item.get("unit_cost_gbp", 0.0))

                col_e = st.columns(2)
                with col_e[0]:
                    edit_price = st.number_input(
                        "Unit price",
                        min_value=0.0,
                        value=current_price,
                        step=0.0001,
                        format="%.2f",
                    )
                with col_e[1]:
                    edit_currency = st.selectbox(
                        "Currency",
                        ["USD", "GBP"],
                        index=0 if current_currency == "USD" else 1,
                    )

                edit_num_welds = st.number_input(
                    "No. welds",
                    min_value=1,
                    value=int(selected_item.get("num_welds", 1)),
                    step=1,
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
                    elif edit_price <= 0:
                        st.error("Unit price must be > 0.")
                    elif edit_num_welds <= 0:
                        st.error("Number of welds must be > 0.")
                    else:
                        selected_item["id"] = edit_id.strip()
                        selected_item["name"] = edit_name.strip()
                        selected_item["currency"] = edit_currency
                        selected_item["num_welds"] = int(edit_num_welds)

                        if edit_currency == "USD":
                            selected_item["unit_cost_usd"] = float(edit_price)
                            selected_item.pop("unit_cost_gbp", None)
                        else:
                            selected_item["unit_cost_gbp"] = float(edit_price)
                            selected_item.pop("unit_cost_usd", None)

                        if edit_notes.strip():
                            selected_item["notes"] = edit_notes.strip()
                        else:
                            selected_item.pop("notes", None)

                        weld_heads[idx] = selected_item
                        materials_db["Weld heads"] = weld_heads
                        save_materials(materials_db)

                        st.success("Weld head updated successfully ✅")
                        st.rerun()

    # ------------------ DELETE ITEM ------------------
    if weld_heads:
        st.markdown("---")
        with st.expander("🗑️ Delete Weld head", expanded=False):
            labels_del = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(weld_heads)
            ]
            selected_del = st.selectbox(
                "Select weld head to delete",
                labels_del,
                key="delete_weld_head_select",
            )
            idx_del = int(selected_del.split(":", 1)[0])

            if st.button("Delete selected weld head"):
                removed = weld_heads.pop(idx_del)
                materials_db["Weld heads"] = weld_heads
                save_materials(materials_db)

                st.warning(
                    f"Deleted: {removed.get('id', '(no id)')} – "
                    f"{removed.get('name', '(no name)')}"
                )
                st.rerun()
