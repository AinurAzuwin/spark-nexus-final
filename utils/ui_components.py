# Buttons, cards, layout helpers

import streamlit as st

def render_footer():
    """Renders a blue footer with copyright information at the bottom of every page."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-bottom: 60px !important; /* Space for footer */
        }
        .footer {
            position: fixed !important;
            left: 0 !important;
            bottom: 0 !important;
            width: 100% !important;
            background-color: #004280 !important; /* Custom background */
            color: white !important;
            text-align: center !important;
            padding: 10px !important;
            font-size: 14px !important;
            z-index: 1000 !important;
        }
        </style>
        <div class="footer">
            © 2025 Halo Child, Sponsored by Advantech
        </div>
        """,
        unsafe_allow_html=True
    )
