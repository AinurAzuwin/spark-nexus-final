import streamlit as st
from utils.session_state import set_logged_in_session
from utils.ui_components import render_footer
from database.users import (
    get_all_users,
    get_all_therapists,
    register_new_user,
    assign_therapist_to_child,
    get_pending_therapists,
    approve_therapist_user,
    authenticate_user_service
)

def logout(cookies):
    """Clears session state and cookies for logout and forces a rerun."""
    from utils.session_state import clear_cookies
    # Clear cookies
    clear_cookies(cookies)
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

def render_approval_management():
    """Renders the section for reviewing, approving, and manually registering therapist accounts."""

    # --- 1. Pending Approval Section ---
    st.subheader("Pending Therapist Approvals")

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

                col_approve, col_reject = st.columns([1, 2])

                with col_approve:
                    # Button to approve the user
                    if st.button(f"✅ Approve User", key=f"approve_btn_{i}", type="primary", use_container_width=True):
                        if approve_therapist_user(user_email):
                            st.success(f"Account for {user_name} has been **APPROVED**.")
                            st.rerun() # Rerun to refresh the list
                        else:
                            st.error(f"Failed to approve account {user_email}. Check database logs.")

                with col_reject:
                    # Placeholder for rejection logic (requires database delete function)
                    st.button(f"❌ Reject (Requires Delete Logic)", key=f"reject_btn_{i}", use_container_width=True, disabled=True)
                    st.caption("Rejection/Deletion logic is not yet implemented.")

    st.markdown("---")

    # --- 2. Manual Registration Section ---
    st.subheader("Register New Therapist Manually (Immediate Approval)")

    with st.form("new_therapist_form"):
        name = st.text_input("Full Name (Manual Register)")
        email = st.text_input("Email (Login ID)", key="manual_email_input").lower()
        password = st.text_input("Temporary Password", type="password", key="manual_password_input")
        license_id = st.text_input("Professional License ID (Required)")

        if st.form_submit_button("Create & Approve Therapist"):
            if not email or not password or not name:
                st.error("Name, Email, and Password are required.")
            elif not license_id:
                st.error("License/Registration ID is required for Therapist registration.")
            else:
                # 1. Register the user (defaults to PENDING in DB)
                result = register_new_user(email, password, role="THERAPIST", name=name, license_id=license_id)

                if result is True:
                    # 2. Immediately approve the manually created account
                    if approve_therapist_user(email):
                        st.success(f"Therapist {name} registered and **APPROVED** successfully.")
                        st.rerun()
                    else:
                        st.error(f"Therapist {name} registered, but immediate approval failed. Please approve manually.")
                elif result == "User already exists":
                    st.warning(f"Therapist account with email **{email}** already exists. Check status in the table.")
                else:
                    st.error(f"Therapist registration failed: {result}")


def render_therapist_registration():
    """DEPRECATED: Content moved to render_approval_management."""
    pass # This function is now empty


def render_user_management(users):
    """Display all users in a table for overview/deletion."""
    st.subheader("All System Users")

    # Prepare data for display
    user_data = []
    for user in users:
        # Added Status and License ID to the user management overview
        user_data.append({
            'ID': user.get('UserID', 'N/A'),
            'Role': user.get('UserRole', 'UNKNOWN'),
            'Name': user.get('FullName', 'N/A'),
            'Email': user.get('Email', 'N/A'),
            'Status': user.get('Approved', 'N/A'),
            'LicenseID': user.get('LicenseID', 'N/A')
        })

    st.dataframe(user_data, use_container_width=True)

    # Placeholder for Delete User logic
    st.markdown("---")
    st.info("User deletion feature pending implementation.")


def render_assignment_management(all_therapists, all_users):
    """Allows Admin to link a Parent's child to a specific Therapist."""
    st.subheader("Assign Therapist to Child")
    st.caption("Only **approved** therapists are available for assignment below.")

    from database.children import get_children_by_parent
    parents = [u for u in all_users if u['UserRole'] == 'PARENT']
    unassigned_children = []
    for parent in parents:
        children = get_children_by_parent(parent['UserID'])
        for child in children:
            if not child.get('TherapistID'):
                unassigned_children.append(child)

    if not unassigned_children:
        st.info("All registered children have been assigned a therapist.")
        return

    # 1. Select Child
    child_options = {f"{c['Name']} (Parent: {next((p['FullName'] for p in parents if p['UserID'] == c['ParentID']), 'Unknown')})": c['ChildID'] for c in unassigned_children}
    selected_child_key = st.selectbox("Select Child to Assign:", options=list(child_options.keys()))

    if not selected_child_key:
        return

    selected_child_id = child_options[selected_child_key]
    selected_child = next(c for c in unassigned_children if c['ChildID'] == selected_child_id)

    # 2. Select Therapist (Only show APPROVED therapists)
    approved_therapists = get_all_therapists()

    if not approved_therapists:
        st.warning("No **approved** therapists are available for assignment. Check the 'Therapist Approvals' tab.")
        return

    therapist_options = {f"{t['FullName']} ({t['Email']})": t['UserID'] for t in approved_therapists}
    selected_therapist_key = st.selectbox("Select Approved Therapist:", options=list(therapist_options.keys()))

    if not selected_therapist_key:
        return

    selected_therapist_id = therapist_options[selected_therapist_key]
    selected_therapist_name = selected_therapist_key.split(' (')[0]

    if st.button("Confirm Assignment"):
        from database.children import assign_therapist_to_child
        if assign_therapist_to_child(selected_child_id, selected_therapist_id, selected_therapist_name):
            st.success(f"{selected_child['Name']} successfully assigned to {selected_therapist_name}!")
            st.rerun()
        else:
            st.error("Assignment failed. Check logs.")


def admin_dashboard_ui(cookies):
    """Main rendering function for the Admin Dashboard."""

    st.title("⚙️ Admin Control Panel")
    st.markdown(f"Welcome, {st.session_state.get('full_name', 'Admin')}!")

    # Sidebar for navigation
    with st.sidebar:
        st.header("Navigation")
        if st.button("🚪 **Logout**", help="Click to securely log out"):
            logout(cookies)

    # Fetch data once for all tabs
    all_users = get_all_users()
    # Note: get_all_therapists will now only return APPROVED therapists from the DB
    all_therapists = get_all_therapists()

    # Use tabs for clear organization
    # Renamed Tab 3 to focus on Approvals
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "User Management",
        "Assignment",
        "Therapist Approvals",
        "Data Management",
        "Analytics Overview"
    ])

    with tab1:
        render_user_management(all_users)

    with tab2:
        # Note: render_assignment_management is now using the filtered list of APPROVED therapists
        render_assignment_management(all_therapists, all_users)

    with tab3:
        # New tab for approval logic
        render_approval_management()

    with tab4:
        from pages.admin.data_management import admin_data_management_ui
        admin_data_management_ui()

    with tab5:
        from pages.admin.analytics_overview import admin_analytics_overview_ui
        admin_analytics_overview_ui()

    # Render the footer
    from utils.ui_components import render_footer

render_footer()
