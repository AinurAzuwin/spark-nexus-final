import streamlit as st
from streamlit_option_menu import option_menu
from database.users import (
    get_pending_therapists,
    approve_therapist_user,
    register_new_user,
    delete_user
)
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
from datetime import datetime


def logout():
    """Clears session state and cookies for logout and forces a rerun."""
    # Clear cookies
    clear_cookies(st.session_state.get('cookies'))
    # Clear session state keys related to the logged-in user
    if 'logged_in' in st.session_state:
        del st.session_state['logged_in']
    if 'user_id' in st.session_state:
        del st.session_state['user_id']
    if 'user_role' in st.session_state:
        del st.session_state['user_role']
    if 'full_name' in st.session_state:
        del st.session_state['full_name']
    if 'user_email' in st.session_state:
        del st.session_state['user_email']

    # Rerun the app to go back to the main login/home page
    st.rerun()

# Logout button in sidebar
with st.sidebar:
    if st.button("Logout", icon=":material/logout:", help="Click to securely log out", use_container_width=True):
        logout()

st.markdown("""
    <style>
        .safe-header {
            background-color: #004280;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="safe-header">
    <h2 style="margin: 0;">Therapist Approval</h2>
    <p style="margin: 0;">Approve pending therapist accounts and register new ones manually.</p>
</div>
""", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None,
    options=["Pending Therapist Approval", "Register New Therapist Manually"],
    icons=["bi-clock", "bi-person-plus"],
    default_index=0,
    orientation="horizontal",
)

if selected == "Pending Therapist Approval":
    # Fetch pending therapists using the new function
    pending_therapists = get_pending_therapists()

    if not pending_therapists:
        st.info("🎉 No therapist accounts are currently pending approval from general sign-up.")
    else:
        st.warning(f"You have **{len(pending_therapists)}** accounts requiring review.")

        for i, user in enumerate(pending_therapists):
            user_email = user.get('Email', 'N/A')
            user_name = user.get('FullName', 'Anonymous')

            # Use a unique key for each expander
            with st.expander(f"Review Pending: {user_name} ({user_email})", expanded=False):
                st.markdown(f"**Email:** `{user_email}`")
                st.markdown(f"**Role:** {user.get('UserRole')}")
                # Ensure the LicenseID is prominently displayed for verification
                st.markdown(f"**License/Registration ID:** `{user.get('LicenseID', 'N/A')}`")
                st.caption(f"Registered User ID: {user.get('UserID')}")

                col_approve, col_reject = st.columns(2)

                with col_approve:
                    # Button to approve the user
                    if st.button(f"✅ Approve User", key=f"approve_btn_{i}", type="primary", use_container_width=True):
                        if approve_therapist_user(user_email):
                            st.success(f"Account for {user_name} has been **APPROVED**.")
                            st.rerun() # Rerun to refresh the list
                        else:
                            st.error(f"Failed to approve account {user_email}. Check database logs.")

                with col_reject:
                    # Button to reject and delete the user
                    if st.button(f"❌ Reject & Delete User", key=f"reject_btn_{i}", use_container_width=True):
                        if delete_user(user_email):
                            st.success(f"Account for {user_name} has been **REJECTED and DELETED**.")
                            st.rerun()  # Rerun to refresh the list
                        else:
                            st.error(f"Failed to reject and delete account {user_email}. Check database logs.")

elif selected == "Register New Therapist Manually":

    # Display messages above the form
    if 'form_message' in st.session_state:
        if st.session_state['form_message_type'] == 'error':
            st.error(st.session_state['form_message'])
        elif st.session_state['form_message_type'] == 'success':
            st.success(st.session_state['form_message'])
        elif st.session_state['form_message_type'] == 'warning':
            st.warning(st.session_state['form_message'])
        # Clear the message after displaying
        del st.session_state['form_message']
        del st.session_state['form_message_type']

    with st.form("new_therapist_form"):
        st.markdown("Full Name <span style='color:red;'>*</span>", unsafe_allow_html=True)
        name = st.text_input("", label_visibility="collapsed", key="name")
        st.markdown("Email (Login ID) <span style='color:red;'>*</span>", unsafe_allow_html=True)
        email = st.text_input("", label_visibility="collapsed", key="manual_email_input").lower()
        st.markdown("Temporary Password <span style='color:red;'>*</span>", unsafe_allow_html=True)
        password = st.text_input("", label_visibility="collapsed", type="password", key="manual_password_input")
        st.markdown("Professional License ID <span style='color:red;'>*</span>", unsafe_allow_html=True)
        license_id = st.text_input("", label_visibility="collapsed", key="license_id")
        st.divider()
        submitted = st.form_submit_button("Create & Approve Therapist",type="primary", use_container_width=True)
        if submitted:
            if not name or not email or not password or not license_id:
                st.session_state['form_message'] = "All fields are required. Please fill in Full Name, Email, Temporary Password, and Professional License ID."
                st.session_state['form_message_type'] = 'error'
            else:
                # 1. Register the user (defaults to PENDING in DB)
                result = register_new_user(email, password, role="THERAPIST", full_name=name, license_id=license_id, contact_number=None, registration_date= datetime.utcnow().isoformat())

                if result is True:
                    # 2. Immediately approve the manually created account
                    if approve_therapist_user(email):
                        st.session_state['form_message'] = f"Therapist {name} registered and **APPROVED** successfully."
                        st.session_state['form_message_type'] = 'success'
                    else:
                        st.session_state['form_message'] = f"Therapist {name} registered, but immediate approval failed. Please approve manually."
                        st.session_state['form_message_type'] = 'error'
                elif result == "User already exists":
                    st.session_state['form_message'] = f"Therapist account with email **{email}** already exists. Check status in the table."
                    st.session_state['form_message_type'] = 'warning'
                else:
                    st.session_state['form_message'] = f"Therapist registration failed: {result}"
                    st.session_state['form_message_type'] = 'error'
            st.rerun()

render_footer()
