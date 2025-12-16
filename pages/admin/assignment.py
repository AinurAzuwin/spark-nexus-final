import streamlit as st
import pandas as pd
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
from database.children import get_all_children
from database.users import get_user_by_id

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
    <h2 style="margin: 0;">Assignment</h2>
    <p style="margin: 0;">Assign children to therapists.</p>
</div>
""", unsafe_allow_html=True)

# Fetch all children data
children = get_all_children()

if children:
    # Prepare data for display
    df = pd.DataFrame(children)
    # Select relevant columns for monitoring
    df = df[['Name', 'DOB', 'ParentID', 'TherapistName']]
    # Handle cases where no therapist is assigned
    df['TherapistName'] = df['TherapistName'].fillna('Not Assigned')
    # Get parent names instead of IDs
    df['ParentName'] = df['ParentID'].apply(lambda pid: get_user_by_id(pid).get('FullName', 'Unknown') if pid else 'Unknown')
    # Select and rename columns for better readability
    df = df[['Name', 'DOB', 'ParentName', 'TherapistName']]
    df.columns = ['Child Name', 'Date of Birth', 'Parent Name', 'Assigned Therapist']
    
    st.subheader("All Children and Their Assigned Therapists")
    st.dataframe(df, use_container_width=True)
else:
    st.write("No children found.")

render_footer()