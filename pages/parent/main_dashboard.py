import streamlit as st
from database.children import get_children_by_parent
from database.sessions import get_sessions_by_child
from database.reports import get_reports_by_child
from database.appointments import get_appointments_by_parent, get_upcoming_approved_appointments_by_parent
from utils.ui_components import render_footer

from utils.session_state import clear_cookies

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

# SAFE HEADER (inside main container)
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
    <h2 style="margin: 0;">Parent Dashboard</h2>
    <p style="margin: 0;">Overview of your child's total sessions, approved reports, and appointments.</p>
</div>
""", unsafe_allow_html=True)
st.markdown(f"Welcome, {st.session_state.get('full_name', 'Parent')}!")

parent_id = st.session_state.get('user_id')

# Overview cards
col1, col2, col3, col4 = st.columns(4)
children = get_children_by_parent(parent_id)
with col1:
    st.metric("Children", len(children))
with col2:
    total_sessions = sum(len(get_sessions_by_child(child['ChildID'])) for child in children)
    st.metric("Total Sessions", total_sessions)
with col3:
    total_reports = sum(len([r for r in get_reports_by_child(child['ChildID']) if r.get('Approved', False)]) for child in children)
    st.metric("Approved Reports", total_reports)
with col4:
    total_appts = len(get_appointments_by_parent(parent_id))
    st.metric("Appointments", total_appts)

st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("Recent Activity")
    # Show recent sessions or reports
    for child in children[:3]:  # Limit to first 3 children
        st.write(f"**{child['Name']}**")
        sessions = get_sessions_by_child(child['ChildID'])
        if sessions:
            latest = max(sessions, key=lambda x: x.get('created_at', x['session_id']))
            session_date = latest.get('created_at', 'Unknown date').split('T')[0] if latest.get('created_at') else 'Unknown date'
            st.write(f"Last session: Session {latest['session_number']} on {session_date}")
        else:
            st.write("No sessions yet.")

with col2:
    st.subheader("Upcoming Appointments")
    upcoming_appts = get_upcoming_approved_appointments_by_parent(parent_id)
    if upcoming_appts:
        # Create a dict for child names
        child_dict = {child['ChildID']: child['Name'] for child in children}
        for appt in upcoming_appts:
            child_name = child_dict.get(appt['ChildID'], 'Unknown Child')
            st.write(f"**{child_name}** - {appt['DateTime']}")
    else:
        st.write("No upcoming appointments.")

render_footer()
