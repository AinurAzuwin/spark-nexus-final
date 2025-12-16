import streamlit as st
from streamlit_option_menu import option_menu
from database.appointments import get_appointments_by_therapist, update_appointment_status
from database.children import get_children_by_therapist
from database.users import get_user_by_id
from utils.session_state import clear_cookies
from utils.ui_components import render_footer

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
    <h2 style="margin: 0;">Appointment Approval</h2>
    <p style="margin: 0;">Review and approve or reject appointment requests.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<style>
        .st-key-green button {
            background-color: green !important;
            color: white !important;
        }
        .st-key-red button {
            background-color: red !important;
            color: white !important;
        }
</style>
""", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None,
    options=["Pending", "Approved", "Rejected"],
    icons=["bi-clock", "bi-check-circle", "bi-x-circle"],
    default_index=0,
    orientation="horizontal",
)

therapist_id = st.session_state.get('user_id')
appts = get_appointments_by_therapist(therapist_id)
children = get_children_by_therapist(therapist_id)
child_dict = {c['ChildID']: c['Name'] for c in children}
parent_dict = {c['ChildID']: c['ParentID'] for c in children}

if selected == "Pending":
    filtered_appts = [appt for appt in appts if appt['Status'] == 'PENDING']
    if filtered_appts:
        for appt in sorted(filtered_appts, key=lambda x: x['DateTime']):
            child_name = child_dict.get(appt['ChildID'], f"Child {appt['ChildID']}")
            date, time = appt['DateTime'].split(' ')
            with st.expander(f"{child_name} on {date} ({time})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Child:** {child_name}")
                    date, time = appt['DateTime'].split(' ')
                    st.markdown(f"**Date:** {date}")
                    st.markdown(f"**Time:** {time}")
                    st.markdown(f"**Status:** <span style='color:#FFC000;'>{appt['Status']}</span>", unsafe_allow_html=True)
                with col2:
                    parent_id = parent_dict.get(appt['ChildID'])
                    if parent_id:
                        parent = get_user_by_id(parent_id)
                        if parent:
                            st.markdown(f"**Parent Name:** {parent.get('FullName', 'N/A')}")
                            st.markdown(f"**Parent Phone:** {parent.get('ContactNumber', 'N/A')}")
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('<div class="st-key-green">', unsafe_allow_html=True)
                    if st.button("✅ Approve", key=f"approve_{appt['AppointmentID']}", use_container_width=True, type="primary"):
                        update_appointment_status(appt['AppointmentID'], 'APPROVED')
                        st.success("Approved!")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                with col2:
                    rejection_note = st.text_area("Rejection Note (Optional)", key=f"note_{appt['AppointmentID']}", height=100)
                    st.markdown('<div class="st-key-red">', unsafe_allow_html=True)
                    if st.button("❌ Reject", key=f"reject_{appt['AppointmentID']}", use_container_width=True, type="primary"):
                        update_appointment_status(appt['AppointmentID'], 'REJECTED', rejection_note if rejection_note else None)
                        st.success("Rejected!")
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.write("No pending appointments.")
elif selected == "Approved":
    filtered_appts = [appt for appt in appts if appt['Status'] == 'APPROVED']
    if filtered_appts:
        table_data = []
        for appt in sorted(filtered_appts, key=lambda x: x['DateTime']):
            child_name = child_dict.get(appt['ChildID'], f"Child {appt['ChildID']}")
            table_data.append({
                'DateTime': appt['DateTime'],
                'Child Name': child_name,
                'Status': appt['Status']
            })
        st.dataframe(table_data)
    else:
        st.write("No approved appointments.")
elif selected == "Rejected":
    filtered_appts = [appt for appt in appts if appt['Status'] == 'REJECTED']
    if filtered_appts:
        table_data = []
        for appt in sorted(filtered_appts, key=lambda x: x['DateTime']):
            child_name = child_dict.get(appt['ChildID'], f"Child {appt['ChildID']}")
            rejection_note = appt.get('RejectionNote', '')
            table_data.append({
                'DateTime': appt['DateTime'],
                'Child Name': child_name,
                'Status': appt['Status'],
                'Rejection Note': rejection_note
            })
        st.dataframe(table_data)
    else:
        st.write("No rejected appointments.")

render_footer()

