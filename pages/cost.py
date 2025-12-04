import streamlit as st

from model import load_product


def render() -> None:
    """Cost page – for now just shows core inputs and derived geometry."""
    st.title("Cost per Array")

    product = load_product()

    st.subheader("Product Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Product name", value=product.name)
        st.metric("Cells per string", value=product.cells_per_string)
        st.metric("Strings per array", value=product.strings_per_array)
        st.metric("Total cells per array", value=product.cells_per_array)

    with col2:
        st.metric(
            "String length (mm)",
            value=f"{product.total_string_length_mm:.2f}",
        )
        st.metric(
            "String length (cm)",
            value=f"{product.total_string_length_mm / 10.0:.2f}",
        )
        st.metric(
            "String length (m)",
            value=f"{product.total_string_length_mm / 1000.0:.3f}",
        )
        st.metric(
            "Exchange rate (GBP per USD)",
            value=f"{product.exchange_rate_gbp_per_usd:.2f}",
        )

    st.subheader("Cost Summary (placeholder)")
    st.warning("Total cost per array: **TBD** – materials and costing logic not yet implemented.")
