import streamlit as st

from model import (
    load_materials,
    save_materials,
    load_product,
    MaterialItem,
)


SILVER_DENSITY_DEFAULT = 10.49  # g/cm^3 (approx pure silver)


def compute_cost_per_mm_gbp(item: MaterialItem, exchange_rate_gbp_per_usd: float) -> float:
    """
    Compute derived cost per mm in GBP for a given silver ribbon item.

    Uses:
    - width_mm
    - thickness_mm
    - density_g_cm3 (default 10.49 if missing)
    - price_per_g
    - price_currency ("USD" or "GBP")

    Formula:
    mass_per_mm = density * width_mm * thickness_mm / 1000
    (with width/thickness in mm, density in g/cm^3)

    cost_per_mm_gbp = mass_per_mm * price_per_g_in_GBP
    """
    try:
        width_mm = float(item.get("width_mm", 0.0))
        thickness_mm = float(item.get("thickness_mm", 0.0))
        density = float(item.get("density_g_cm3", SILVER_DENSITY_DEFAULT))
        price_per_g = float(item.get("price_per_g", 0.0))
    except (TypeError, ValueError):
        return 0.0

    if width_mm <= 0 or thickness_mm <= 0 or density <= 0 or price_per_g <= 0:
        return 0.0

    currency = (item.get("price_currency", "USD") or "USD").upper()

    # Convert price_per_g to GBP/g
    if currency == "USD":
        price_per_g_gbp = price_per_g * float(exchange_rate_gbp_per_usd)
    else:  # assume already GBP
        price_per_g_gbp = price_per_g

    # mass per mm (g/mm)
    # mass_per_mm = density[g/cm3] * width_mm[mm] * thickness_mm[mm] / 1000
    mass_per_mm = density * width_mm * thickness_mm / 1000.0

    cost_per_mm_gbp = mass_per_mm * price_per_g_gbp
    return cost_per_mm_gbp


def render() -> None:
    """Full CRUD UI for Silver Ribbon materials."""
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    st.title("Silver Ribbon Materials")

    st.markdown(
        f"""
        Current exchange rate (GBP per USD): **{exchange_rate:.2f}**

        For each ribbon, you enter **price per gram** (USD/g or GBP/g),
        **width**, and **thickness**. The app derives **cost per mm in GBP**
        using silver density (~{SILVER_DENSITY_DEFAULT} g/cm³).
        """
    )

    materials_db = load_materials()
    silver_items = materials_db.get("Silver Ribbon", [])

    # ------------------ LIST ITEMS ------------------
    st.markdown("### Current Silver Ribbon items")

    if silver_items:
        # Build display table with derived cost/mm
        rows = []
        for item in silver_items:
            row = dict(item)  # copy to avoid mutating stored YAML data
            cost_per_mm_gbp = compute_cost_per_mm_gbp(item, exchange_rate)
            row["cost_per_mm_gbp (derived)"] = (
                f"{cost_per_mm_gbp:.8f}" if cost_per_mm_gbp > 0 else "-"
            )
            rows.append(row)

        st.table(rows)
    else:
        st.info("No Silver Ribbon items defined yet. Add one below.")

    st.markdown("---")

    # ------------------ ADD NEW ITEM ------------------
    with st.expander("➕ Add new Silver Ribbon item", expanded=False):
        with st.form("add_silver_item"):
            st.markdown("Define a new Silver Ribbon material entry.")

            new_id = st.text_input("ID / Code", value="")
            new_name = st.text_input("Name / Description", value="")

            col_dims = st.columns(3)
            with col_dims[0]:
                width_mm = st.number_input(
                    "Width (mm)",
                    min_value=0.0,
                    value=2.0,
                    step=0.1,
                    format="%.3f",
                )
            with col_dims[1]:
                thickness_mm = st.number_input(
                    "Thickness (mm)",
                    min_value=0.0,
                    value=0.0254,  # current default
                    step=0.001,
                    format="%.2f",
                )
            with col_dims[2]:
                density_g_cm3 = st.number_input(
                    "Density (g/cm³)",
                    min_value=0.0,
                    value=float(SILVER_DENSITY_DEFAULT),
                    step=0.01,
                    format="%.3f",
                )

            col_price = st.columns(2)
            with col_price[0]:
                price_per_g = st.number_input(
                    "Price per gram",
                    min_value=0.0,
                    value=0.0,
                    step=0.0001,
                    format="%.2f",
                )
            with col_price[1]:
                price_currency = st.selectbox(
                    "Price currency",
                    options=["USD", "GBP"],
                    index=0,
                )

            new_notes = st.text_area("Notes (optional)", value="")

            submitted = st.form_submit_button("Add item")

            if submitted:
                if not new_id.strip():
                    st.error("Please provide an ID / Code.")
                elif not new_name.strip():
                    st.error("Please provide a Name / Description.")
                elif width_mm <= 0 or thickness_mm <= 0 or density_g_cm3 <= 0:
                    st.error("Width, thickness and density must be > 0.")
                elif price_per_g <= 0:
                    st.error("Price per gram must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "width_mm": float(width_mm),
                        "thickness_mm": float(thickness_mm),
                        "density_g_cm3": float(density_g_cm3),
                        "price_per_g": float(price_per_g),
                        "price_currency": price_currency,
                    }
                    if new_notes.strip():
                        item["notes"] = new_notes.strip()

                    silver_items.append(item)
                    materials_db["Silver Ribbon"] = silver_items
                    save_materials(materials_db)

                    st.success("Silver Ribbon item added and saved to materials.yaml ✅")
                    st.rerun()

    st.markdown("---")

    # ------------------ EDIT ITEM ------------------
    if silver_items:
        with st.expander("✏️ Edit existing Silver Ribbon item", expanded=False):
            labels = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(silver_items)
            ]
            selected_label = st.selectbox("Select item to edit", labels)
            selected_index = int(selected_label.split(":", 1)[0])
            selected_item = silver_items[selected_index]

            with st.form("edit_silver_item"):
                edit_id = st.text_input("ID / Code", value=selected_item.get("id", ""))
                edit_name = st.text_input(
                    "Name / Description", value=selected_item.get("name", "")
                )

                col_dims_e = st.columns(3)
                with col_dims_e[0]:
                    edit_width_mm = st.number_input(
                        "Width (mm)",
                        min_value=0.0,
                        value=float(selected_item.get("width_mm", 0.0)),
                        step=0.1,
                        format="%.3f",
                    )
                with col_dims_e[1]:
                    edit_thickness_mm = st.number_input(
                        "Thickness (mm)",
                        min_value=0.0,
                        value=float(selected_item.get("thickness_mm", 0.0)),
                        step=0.001,
                        format="%.2f",
                    )
                with col_dims_e[2]:
                    edit_density_g_cm3 = st.number_input(
                        "Density (g/cm³)",
                        min_value=0.0,
                        value=float(
                            selected_item.get(
                                "density_g_cm3", SILVER_DENSITY_DEFAULT
                            )
                        ),
                        step=0.01,
                        format="%.3f",
                    )

                col_price_e = st.columns(2)
                with col_price_e[0]:
                    edit_price_per_g = st.number_input(
                        "Price per gram",
                        min_value=0.0,
                        value=float(selected_item.get("price_per_g", 0.0)),
                        step=0.0001,
                        format="%.2f",
                    )
                with col_price_e[1]:
                    current_currency = (
                        selected_item.get("price_currency", "USD") or "USD"
                    ).upper()
                    edit_price_currency = st.selectbox(
                        "Price currency",
                        options=["USD", "GBP"],
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
                    elif edit_width_mm <= 0 or edit_thickness_mm <= 0 or edit_density_g_cm3 <= 0:
                        st.error("Width, thickness and density must be > 0.")
                    elif edit_price_per_g <= 0:
                        st.error("Price per gram must be > 0.")
                    else:
                        selected_item["id"] = edit_id.strip()
                        selected_item["name"] = edit_name.strip()
                        selected_item["width_mm"] = float(edit_width_mm)
                        selected_item["thickness_mm"] = float(edit_thickness_mm)
                        selected_item["density_g_cm3"] = float(edit_density_g_cm3)
                        selected_item["price_per_g"] = float(edit_price_per_g)
                        selected_item["price_currency"] = edit_price_currency

                        if edit_notes.strip():
                            selected_item["notes"] = edit_notes.strip()
                        else:
                            selected_item.pop("notes", None)

                        silver_items[selected_index] = selected_item
                        materials_db["Silver Ribbon"] = silver_items
                        save_materials(materials_db)

                        st.success("Item updated successfully ✅")
                        st.rerun()

    # ------------------ DELETE ITEM ------------------
    if silver_items:
        st.markdown("---")
        with st.expander("🗑️ Delete Silver Ribbon item", expanded=False):
            labels_del = [
                f"{idx}: {item.get('id', '(no id)')} – {item.get('name', '(no name)')}"
                for idx, item in enumerate(silver_items)
            ]
            selected_label_del = st.selectbox(
                "Select item to delete",
                labels_del,
                key="delete_silver_select",
            )
            selected_index_del = int(selected_label_del.split(":", 1)[0])

            if st.button("Delete selected item"):
                removed = silver_items.pop(selected_index_del)
                materials_db["Silver Ribbon"] = silver_items
                save_materials(materials_db)

                st.warning(
                    f"Deleted: {removed.get('id', '(no id)')} – {removed.get('name', '(no name)')}"
                )
                st.rerun()
