import streamlit as st


def render_placeholder(category: str) -> None:
    """Placeholder page for material categories not yet implemented."""
    st.title(f"{category} Materials")

    st.info(
        "This materials category does not have a dedicated page yet. "
        "We’ll add a full CRUD interface here soon."
    )
