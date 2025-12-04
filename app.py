import streamlit as st
from pathlib import Path

from model import MATERIAL_CATEGORIES

# Page renderers
from pages.home import render as render_home
from pages.cost import render as render_cost_placeholder
from pages.materials import render_placeholder
from pages.materials_silver import render as render_silver_ribbon


def main() -> None:
    # ---------------------------------------------------
    # Basic page config
    # ---------------------------------------------------
    st.set_page_config(
        page_title="MAT Array Costing Tool",
        page_icon="💸",
        layout="wide",
    )

    # ---------------------------------------------------
    # Hide Streamlit's default multipage navigation
    # ---------------------------------------------------
    st.markdown(
        """
        <style>
        section[data-testid="stSidebarNav"],
        div[data-testid="stSidebarNav"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------
    # Custom sidebar styling (deep blue, white text)
    # ---------------------------------------------------
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background-color: #000065;
        }
        [data-testid="stSidebar"] * {
            color: white !important;
        }

        /* Light indentation for submenu items */
        .cost-submenu {
            padding-left: 15px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------
    # SIDEBAR CONTENT
    # ---------------------------------------------------
    with st.sidebar:
        # Logo
        logo_path = Path("logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_container_width=True)

        st.markdown("---")
        st.title("Navigation")

        # 🔹 Add Labour as a top-level section
        main_page = st.radio(
            "Main section",
            ("Home", "Array Designs", "Materials", "Cost", "Labour"),
            index=0,
        )

        # ---- Submenus ----
        material_section = None
        cost_section = None

        if main_page == "Materials":
            material_section = st.radio(
                "Materials group",
                MATERIAL_CATEGORIES,
                index=0,
            )

        if main_page == "Cost":
            cost_section = st.radio(
                "Cost breakdown",
                (
                    "Summary",
                    "Silver",
                    "Diodes",
                    "Weld heads",
                    "Lamination",
                    "Tapes",
                    "Misc",
                    "Packaging",
                ),
                index=0,
                key="cost_submenu",
            )

    # ---------------------------------------------------
    # MAIN CONTENT ROUTING
    # ---------------------------------------------------
    if main_page == "Home":
        render_home()

    elif main_page == "Array Designs":
        from pages.array_designs import render as render_array_designs
        render_array_designs()

    elif main_page == "Materials":
        if material_section == "Silver Ribbon":
            render_silver_ribbon()
        elif material_section == "Diodes":
            from pages.materials_diodes import render as render_diodes
            render_diodes()
        elif material_section == "Weld heads":
            from pages.materials_weld_heads import render as render_weld_heads
            render_weld_heads()
        elif material_section == "Lamination":
            from pages.materials_lamination import render as render_lamination
            render_lamination()
        elif material_section == "Tapes":
            from pages.materials_tapes import render as render_tapes
            render_tapes()
        elif material_section == "Misc":
            from pages.materials_misc import render as render_misc
            render_misc()
        elif material_section == "Packaging":
            from pages.materials_packaging import render as render_packaging
            render_packaging()
        else:
            render_placeholder(material_section or "Unknown")

    elif main_page == "Cost":
        # Summary (default)
        if cost_section == "Summary":
            from pages.cost_summary import render as render_cost_summary
            render_cost_summary()

        elif cost_section == "Silver":
            from pages.cost_silver import render as render_cost_silver
            render_cost_silver()

        elif cost_section == "Diodes":
            from pages.cost_diodes import render as render_cost_diodes
            render_cost_diodes()

        elif cost_section == "Weld heads":
            from pages.cost_weld_heads import render as render_cost_weld
            render_cost_weld()

        elif cost_section == "Lamination":
            from pages.cost_lamination import render as render_cost_lamination
            render_cost_lamination()

        elif cost_section == "Tapes":
            from pages.cost_tapes import render as render_cost_tapes
            render_cost_tapes()

        elif cost_section == "Misc":
            from pages.cost_misc import render as render_cost_misc
            render_cost_misc()

        elif cost_section == "Packaging":
            from pages.cost_packaging import render as render_cost_packaging
            render_cost_packaging()

        else:
            render_cost_placeholder(cost_section or "Unknown")

    elif main_page == "Labour":
        from pages.cost_labour import render as render_labour
        render_labour()

    else:
        st.error("Unknown page selected.")


if __name__ == "__main__":
    main()
