import streamlit as st

from model import load_materials, save_materials, MaterialItem


def render() -> None:
    """CRUD page for Diodes — very simple unit pricing."""
    st.title("Diodes")

    materials_db = load_materials()
    diodes = materials_db.get("Diodes", [])

    # ------------------ LIST ITEMS ------------------
    st.markdown("### Current Diode items")

    if diodes:
        st.table(diodes)
    else:
        st.info("No diode items yet. Add one below.")

    st.markdown("---")

    # ------------------ ADD NEW ITEM ------------------
    with st.expander("➕ Add new Diode", expanded=False):
        with st.form("add_diode_item"):
            new_id = st.text_input("ID / Code", value="")
            new_name = st.text_input("Name / Description", value="")

            col = st.columns(2)
            with col[0]:
                unit_price = st.number_input(
                    "Unit price",
                    min_value=0.0,
                    value=0.0,
                    step=0.0001,
                    format="%.2f",
                )
            with col[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                )

            new_notes = st.text_area("Notes (optional)", value="")

            submitted = st.form_submit_button("Add diode")

            if submitted:
                if not new_id.strip():
                    st.error("Please provide an ID / Code.")
                elif not new_name.strip():
                    st.error("Please provide a Name / Description.")
                elif unit_price <= 0:
                    st.error("Unit price must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "unit_cost_usd": float(unit_price) if currency == "USD" else None,
                        "unit_cost_gbp": float(unit_price) if currency == "GBP" else None,
                        "currency": currency,
                    }
                    if new_notes.strip():
                        item["notes"] = new_notes.strip()

                    diodes.append(item)
                    materials_db["Diodes"] = diodes
                    save_materials(materials_db)

                    st.success("Diode added and saved to materials.yaml ✅")
                    st.rerun()

    st.markdown("---")

    # ------------------ EDIT ITEM ------------------
    if diodes:
        with st.expander("✏️ Edit existing Diode", expanded=False):
            labels = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(diodes)
            ]
            selected = st.selectbox("Select diode to edit", labels)
            idx = int(selected.split(":")[0])
            selected_item = diodes[idx]

            with st.form("edit_diode_item"):
                edit_id = st.text_input("ID / Code", value=selected_item.get("id", ""))
                edit_name = st.text_input("Name / Description", value=selected_item.get("name", ""))

                # Derive current price + currency
                current_currency = selected_item.get("currency", "USD")
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

                edit_notes = st.text_area("Notes (optional)", value=selected_item.get("notes", ""))

                save_changes = st.form_submit_button("Save changes")

                if save_changes:
                    if not edit_id.strip():
                        st.error("Please provide an ID / Code.")
                    elif not edit_name.strip():
                        st.error("Please provide a Name / Description.")
                    elif edit_price <= 0:
                        st.error("Unit price must be > 0.")
                    else:
                        selected_item["id"] = edit_id.strip()
                        selected_item["name"] = edit_name.strip()
                        selected_item["currency"] = edit_currency

                        # Ensure we store the right price key
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

                        diodes[idx] = selected_item
                        materials_db["Diodes"] = diodes
                        save_materials(materials_db)

                        st.success("Diode updated successfully ✅")
                        st.rerun()

    # ------------------ DELETE ITEM ------------------
    if diodes:
        st.markdown("---")
        with st.expander("🗑️ Delete Diode", expanded=False):
            labels_del = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(diodes)
            ]
            selected_del = st.selectbox(
                "Select diode to delete",
                labels_del,
                key="delete_diode_select",
            )
            idx_del = int(selected_del.split(":")[0])

            if st.button("Delete selected diode"):
                removed = diodes.pop(idx_del)
                materials_db["Diodes"] = diodes
                save_materials(materials_db)

                st.warning(
                    f"Deleted: {removed.get('id', '(no id)')} – {removed.get('name', '(no name)')}"
                )
                st.rerun()
