import streamlit as st
from streamlit_option_menu import option_menu
from database.users import get_all_users, update_user
from database.children import get_all_children, update_child
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
import pandas as pd

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
    <h2 style="margin: 0;">User Management</h2>
    <p style="margin: 0;">Manage children, parents, and therapists data.</p>
</div>
""", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None,
    options=["Children", "Parent", "Therapist"],
    icons=["bi-person", "bi-house", "bi-person-badge"],
    default_index=0,
    orientation="horizontal",
)

if selected == "Children":
    children = get_all_children()
    if children:
        df = pd.DataFrame(children)
        # Remove sensitive fields if any, but for now, allow editing all
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if not edited_df.equals(df):
            st.warning("Changes detected. Click 'Save Changes' to update the database.")
            if st.button("Save Changes", type="primary"):
                # Update each changed row
                for index, row in edited_df.iterrows():
                    original_row = df.iloc[index]
                    updates = {}
                    for col in df.columns:
                        if row[col] != original_row[col]:
                            updates[col] = row[col]
                    if updates:
                        update_child(row['ChildID'], updates)
                st.success("Changes saved successfully!")
                st.rerun()
    else:
        st.info("No children found.")

elif selected == "Parent":
    users = get_all_users()
    parents = [u for u in users if u.get('UserRole') == 'PARENT']
    if parents:
        df = pd.DataFrame(parents)
        # Exclude Password for security
        df = df.drop(columns=['Password'], errors='ignore')
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if not edited_df.equals(df):
            st.warning("Changes detected. Click 'Save Changes' to update the database.")
            if st.button("Save Changes", type="primary"):
                # Update each changed row
                for index, row in edited_df.iterrows():
                    original_row = df.iloc[index]
                    updates = {}
                    for col in df.columns:
                        if row[col] != original_row[col]:
                            updates[col] = row[col]
                    if updates:
                        update_user(row['UserID'], updates)
                st.success("Changes saved successfully!")
                st.rerun()
    else:
        st.info("No parents found.")

elif selected == "Therapist":
    users = get_all_users()
    therapists = [u for u in users if u.get('UserRole') == 'THERAPIST']
    if therapists:
        df = pd.DataFrame(therapists)
        # Exclude Password for security
        df = df.drop(columns=['Password'], errors='ignore')
        edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
        if not edited_df.equals(df):
            st.warning("Changes detected. Click 'Save Changes' to update the database.")
            if st.button("Save Changes", type="primary"):
                # Update each changed row
                for index, row in edited_df.iterrows():
                    original_row = df.iloc[index]
                    updates = {}
                    for col in df.columns:
                        if row[col] != original_row[col]:
                            updates[col] = row[col]
                    if updates:
                        update_user(row['UserID'], updates)
                st.success("Changes saved successfully!")
                st.rerun()
    else:
        st.info("No therapists found.")

render_footer()
