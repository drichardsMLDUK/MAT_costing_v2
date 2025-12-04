import streamlit as st

from model import load_materials, save_materials, load_product, MaterialItem


def compute_kapton_cost_per_disk_gbp(
    item: MaterialItem, exchange_rate_gbp_per_usd: float
) -> float:
    """Compute cost per Kapton disk in GBP."""
    try:
        disks = float(item.get("disks_per_roll", 0))
    except (TypeError, ValueError):
        return 0.0

    if disks <= 0:
        return 0.0

    currency = (item.get("currency", "USD") or "USD").upper()

    try:
        if currency == "USD":
            roll_cost_usd = item.get("roll_cost_usd", None)
            if roll_cost_usd is None:
                return 0.0
            roll_cost_gbp = float(roll_cost_usd) * float(exchange_rate_gbp_per_usd)
        else:
            roll_cost_gbp = float(item.get("roll_cost_gbp", 0.0))
    except (TypeError, ValueError):
        return 0.0

    if roll_cost_gbp <= 0:
        return 0.0

    return roll_cost_gbp / disks


def compute_epoxy_cost_per_ml_gbp(
    item: MaterialItem, exchange_rate_gbp_per_usd: float
) -> float:
    """Compute cost per mL of epoxy in GBP."""
    try:
        volume_ml = float(item.get("volume_ml", 0))
    except (TypeError, ValueError):
        return 0.0

    if volume_ml <= 0:
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

    return total_cost_gbp / volume_ml


def render() -> None:
    product = load_product()
    exchange_rate = product.exchange_rate_gbp_per_usd

    st.title("Misc Materials")

    st.markdown(
        f"""
        Current exchange rate (GBP per USD): **{exchange_rate:2f}**

        This category includes:
        - **Kapton insulation disks**  
          (roll cost + disks per roll → cost per disk in GBP)
        - **Epoxy**  
          (total cost + mL → cost per mL in GBP)
        """
    )

    materials_db = load_materials()
    misc_items = materials_db.get("Misc", [])

    # ------------------ TABLE DISPLAY ------------------
    st.markdown("### Current Misc items")

    if misc_items:
        rows = []
        for item in misc_items:
            row = dict(item)
            m_type = item.get("type", "Unknown")

            if m_type == "Kapton":
                cp = compute_kapton_cost_per_disk_gbp(item, exchange_rate)
                row["derived_cost"] = f"{cp:.6f} £/disk" if cp > 0 else "-"
            elif m_type == "Epoxy":
                cp = compute_epoxy_cost_per_ml_gbp(item, exchange_rate)
                row["derived_cost"] = f"{cp:.6f} £/mL" if cp > 0 else "-"
            else:
                row["derived_cost"] = "-"

            rows.append(row)

        st.table(rows)
    else:
        st.info("No misc materials yet. Add one below.")

    st.markdown("---")

    # =========================================================
    #   ADD NEW KAPTON INSULATION ITEM
    # =========================================================
    with st.expander("➕ Add new Kapton insulation item", expanded=False):
        with st.form("add_kapton_item"):
            new_id = st.text_input("ID / Code", key="kapton_id")
            new_name = st.text_input("Name / Description", key="kapton_name")

            col = st.columns(2)
            with col[0]:
                roll_cost = st.number_input(
                    "Roll cost",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="kapton_roll_cost",
                )
            with col[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                    key="kapton_currency",
                )

            disks_per_roll = st.number_input(
                "Disks per roll",
                min_value=1,
                value=1000,
                step=1,
                key="kapton_disks_per_roll",
            )

            notes = st.text_area(
                "Notes (optional)",
                value="",
                key="kapton_notes",
            )

            submitted = st.form_submit_button("Add Kapton item")

            if submitted:
                if not new_id.strip():
                    st.error("ID required.")
                elif not new_name.strip():
                    st.error("Name required.")
                elif roll_cost <= 0:
                    st.error("Roll cost must be > 0.")
                elif disks_per_roll <= 0:
                    st.error("Disks per roll must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "type": "Kapton",
                        "currency": currency,
                        "disks_per_roll": int(disks_per_roll),
                    }

                    if currency == "USD":
                        item["roll_cost_usd"] = float(roll_cost)
                    else:
                        item["roll_cost_gbp"] = float(roll_cost)

                    if notes.strip():
                        item["notes"] = notes.strip()

                    misc_items.append(item)
                    materials_db["Misc"] = misc_items
                    save_materials(materials_db)

                    st.success("Kapton insulation item added ✅")
                    st.rerun()

    st.markdown("---")

    # =========================================================
    #   ADD NEW EPOXY ITEM
    # =========================================================
    with st.expander("➕ Add new Epoxy item", expanded=False):
        with st.form("add_epoxy_item"):
            new_id = st.text_input("ID / Code", key="epoxy_id")
            new_name = st.text_input("Name / Description", key="epoxy_name")

            col = st.columns(2)
            with col[0]:
                total_cost = st.number_input(
                    "Total cost",
                    min_value=0.0,
                    value=0.0,
                    step=0.01,
                    format="%.2f",
                    key="epoxy_total_cost",
                )
            with col[1]:
                currency = st.selectbox(
                    "Currency",
                    ["USD", "GBP"],
                    index=0,
                    key="epoxy_currency",
                )

            volume_ml = st.number_input(
                "Volume (mL)",
                min_value=0.0,
                value=50.0,
                step=1.0,
                format="%.2f",
                key="epoxy_volume_ml",
            )

            notes = st.text_area(
                "Notes (optional)",
                value="",
                key="epoxy_notes",
            )

            submitted = st.form_submit_button("Add Epoxy item")

            if submitted:
                if not new_id.strip():
                    st.error("ID required.")
                elif not new_name.strip():
                    st.error("Name required.")
                elif total_cost <= 0:
                    st.error("Total cost must be > 0.")
                elif volume_ml <= 0:
                    st.error("Volume must be > 0.")
                else:
                    item: MaterialItem = {
                        "id": new_id.strip(),
                        "name": new_name.strip(),
                        "type": "Epoxy",
                        "currency": currency,
                        "volume_ml": float(volume_ml),
                    }

                    if currency == "USD":
                        item["total_cost_usd"] = float(total_cost)
                    else:
                        item["total_cost_gbp"] = float(total_cost)

                    if notes.strip():
                        item["notes"] = notes.strip()

                    misc_items.append(item)
                    materials_db["Misc"] = misc_items
                    save_materials(materials_db)

                    st.success("Epoxy item added ✅")
                    st.rerun()

    st.markdown("---")

    # =========================================================
    #   DELETE ITEM
    # =========================================================
    if misc_items:
        with st.expander("🗑️ Delete Misc item", expanded=False):
            labels = [
                f"{i}: {item.get('type', '?')} – {item.get('id')} – {item.get('name')}"
                for i, item in enumerate(misc_items)
            ]
            sel = st.selectbox("Select item to delete", labels)

            idx = int(sel.split(":", 1)[0])

            if st.button("Delete selected Misc item"):
                removed = misc_items.pop(idx)
                materials_db["Misc"] = misc_items
                save_materials(materials_db)

                st.warning(
                    f"Deleted {removed.get('type', '?')} – {removed.get('id')}"
                )
                st.rerun()
