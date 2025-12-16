import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
from database.children import get_children_by_parent
from database.appointments import get_appointments_by_parent, create_appointment
from datetime import datetime
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
    <h2 style="margin: 0;">Appointment Management</h2>
    <p style="margin: 0;">Manage Appointment for your child.</p>
</div>
""", unsafe_allow_html=True)

parent_id = st.session_state.get('user_id')
children = get_children_by_parent(parent_id)

selected = option_menu(
    menu_title=None,
    options=["Appointment", "Pending", "Approved", "Rejected"],
    icons=["bi-calendar-event", "bi-clock", "bi-check-circle", "bi-x-circle"],
    default_index=0,
    orientation="horizontal",
)

if selected == "Appointment":
    assigned_children = [c for c in children if c.get('TherapistID')]
    if not assigned_children:
        st.warning("No children with assigned therapists yet.")
    else:
        st.subheader("Book New Appointment")
        with st.form("book_appointment"):
            child_options = {f"{c['Name']} (Therapist: {c['TherapistName']})": c for c in assigned_children}
            st.markdown("**Select Child:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
            selected_child_key = st.selectbox("", list(child_options.keys()), label_visibility="collapsed")
            selected_child = child_options[selected_child_key]
            therapist_id = selected_child['TherapistID']

            # Get available slots
            from database.appointments import get_available_slots
            available_slots = get_available_slots(therapist_id)
            if available_slots:
                # Extract unique dates from available slots
                available_dates = sorted(set(slot.split(' ')[0] for slot in available_slots))
                st.markdown("**Select Date:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
                selected_date = st.selectbox("", available_dates, label_visibility="collapsed")
                # Filter times for the selected date
                available_times = [slot.split(' ')[1] for slot in available_slots if slot.startswith(selected_date)]
                st.markdown("**Select Time:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
                selected_time = st.selectbox("", available_times, label_visibility="collapsed")
                st.divider()
                submitted = st.form_submit_button("Book Appointment", use_container_width=True, type="primary")
                if submitted:
                    appointment_id = f"{parent_id}_{selected_child['ChildID']}_{datetime.now().isoformat()}"
                    create_appointment(appointment_id, selected_child['ChildID'], therapist_id, f"{selected_date} {selected_time}", "PENDING", parent_id=parent_id)
                    st.success("Appointment booked! Waiting for therapist approval.")
            else:
                st.warning("No available slots for this therapist.")
elif selected == "Pending":
    appointments = get_appointments_by_parent(parent_id)
    pending_appointments = [appt for appt in appointments if appt['Status'] == 'PENDING']
    if pending_appointments:
        data = []
        for appt in pending_appointments:
            child_name = next((c['Name'] for c in children if c['ChildID'] == appt['ChildID']), "Unknown")
            data.append({
                "Child Name": child_name,
                "Date & Time": appt['DateTime'],
                "Status": appt['Status']
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No pending appointments.")
elif selected == "Approved":
    appointments = get_appointments_by_parent(parent_id)
    approved_appointments = [appt for appt in appointments if appt['Status'] == 'APPROVED']
    if approved_appointments:
        data = []
        for appt in approved_appointments:
            child_name = next((c['Name'] for c in children if c['ChildID'] == appt['ChildID']), "Unknown")
            data.append({
                "Child Name": child_name,
                "Date & Time": appt['DateTime'],
                "Status": appt['Status']
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No approved appointments.")
elif selected == "Rejected":
    appointments = get_appointments_by_parent(parent_id)
    rejected_appointments = [appt for appt in appointments if appt['Status'] == 'REJECTED']
    if rejected_appointments:
        data = []
        for appt in rejected_appointments:
            child_name = next((c['Name'] for c in children if c['ChildID'] == appt['ChildID']), "Unknown")
            status_display = appt['Status']
            if appt.get('RejectionNote'):
                status_display += f" - {appt['RejectionNote']}"
            data.append({
                "Child Name": child_name,
                "Date & Time": appt['DateTime'],
                "Status": status_display
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No rejected appointments.")

render_footer()
