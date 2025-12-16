import streamlit as st
import pandas as pd
from streamlit_option_menu import option_menu
from database.children import get_children_by_parent, create_child
from database.users import get_user_by_id
from database.children import get_children_by_parent
from database.sessions import get_sessions_by_child
from database.messages import get_messages_by_session
import uuid
from datetime import datetime, timedelta
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

def calculate_age(dob_str):
    """Calculate age from date of birth string."""
    try:
        from datetime import datetime, date
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return "Unknown"

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
    <h2 style="margin: 0;">Child Profiles & Conversation Logs</h2>
    <p style="margin: 0;">View your children's profiles, completed conversation logs and give feedback session.</p>
</div>
""", unsafe_allow_html=True)

parent_id = st.session_state.get('user_id')
children = get_children_by_parent(parent_id)

selected = option_menu(
    menu_title=None,
    options=["Child Profile", "Completed Sessions", "Feedback Session"],
    icons=["bi-person-circle", "bi-chat-dots", "bi-check-circle"],
    default_index=0,
    orientation="horizontal",
)

if selected == "Child Profile":
    if children:
        for child in children:
            age = calculate_age(child['DOB'])
            with st.expander(f"{child['Name']} (Age: {age})"):
                therapist = get_user_by_id(child['TherapistID']) if child.get('TherapistID') else None
                st.write(f"Therapist Name: {therapist['FullName'] if therapist else 'Not assigned yet'}")
                st.write(f"Therapist Email: {therapist.get('Email', 'Unknown') if therapist else 'Unknown'}")
                if st.button(f"View Details for {child['Name']}", key=f"view_{child['ChildID']}", use_container_width=True):
                    st.session_state['selected_child'] = child
                    st.rerun()
                if st.session_state.get('selected_child') == child:
                    st.subheader("Full Child Details")
                    st.write(f"**Name:** {child['Name']}")
                    st.write(f"**Date of Birth:** {child['DOB']}")
                    st.write(f"**Age:** {age}")
                    st.write(f"**IC Number:** {child.get('ICNumber', 'Unknown')}")
                    st.write(f"**Gender:** {child.get('Gender', 'Unknown')}")
                    st.write(f"**Language Background:** {child.get('LanguageBackground', 'Unknown')}")
                    st.write(f"**Diagnosis:** {child.get('Diagnosis', 'None')}")
                    st.write(f"**Therapist Name:** {child.get('TherapistName', 'Unknown')}")
                    if st.button("Close Details", key=f"close_{child['ChildID']}", use_container_width=True, type="primary"):
                        del st.session_state['selected_child']
                        st.rerun()
    else:
        st.write("No children registered yet.")
elif selected == "Completed Sessions":
    if children:
        child_options = {f"{child['Name']} (Age: {calculate_age(child['DOB'])})": child['ChildID'] for child in children}
        selected_child_name = st.selectbox("Select Child:", list(child_options.keys()), key="active_child_select")
        child_name = selected_child_name.split(' (Age:')[0]  # Extract child name
        selected_child_id = child_options[selected_child_name]
        sessions = [s for s in get_sessions_by_child(selected_child_id) if s.get('status') != 'COMPLETED']
        if sessions:
            # Sort sessions by session_number
            sessions_sorted = sorted(sessions, key=lambda s: s['session_number'])
            # Create display numbers starting from 1
            display_numbers = list(range(1, len(sessions_sorted) + 1))
            session_options = {f"Session {display_number}": session for display_number, session in zip(display_numbers, sessions_sorted)}
            selected_session_name = st.selectbox("Select Session:", list(session_options.keys()), key="active_session_select")
            if selected_session_name:
                selected_session = session_options[selected_session_name]
                messages = get_messages_by_session(selected_session['session_id'])
                if messages:
                    st.subheader(f"Conversation Logs for {selected_session_name}")
                    for msg in messages:
                        sender_display = "AI Agent" if msg['Sender'].lower() == "assistant" else (child_name if msg['Sender'].lower() == "user" else msg['Sender'].capitalize())
                        formatted_timestamp = msg['Timestamp'].replace('T', ', ')
                        st.write(f"**{sender_display}:** {msg['Text']} ({formatted_timestamp})")
                else:
                    st.write("No messages in this session.")
        else:
            st.write("No active sessions for this child.")
    else:
        st.write("No children registered yet.")
elif selected == "Feedback Session":
    if children:
        child_options = {f"{child['Name']} (Age: {calculate_age(child['DOB'])})": child['ChildID'] for child in children}
        selected_child_name = st.selectbox("Select Child:", list(child_options.keys()), key="completed_child_select")
        child_name = selected_child_name.split(' (Age:')[0]  # Extract child name
        selected_child_id = child_options[selected_child_name]
        sessions = get_sessions_by_child(selected_child_id)
        if sessions:
            # Sort sessions by session_number
            sessions_sorted = sorted(sessions, key=lambda s: s['session_number'])
            # Create display numbers starting from 1
            display_numbers = list(range(1, len(sessions_sorted) + 1))
            session_options = {f"Session {display_number}": session for display_number, session in zip(display_numbers, sessions_sorted)}
            selected_session_name = st.selectbox("Select Session:", list(session_options.keys()), key="completed_session_select")
            if selected_session_name:
                session = session_options[selected_session_name]
                messages = get_messages_by_session(session['session_id'])
                if messages:
                    st.subheader(f"Conversation Logs for {selected_session_name}")
                    for msg in messages:
                        sender_display = "AI Agent" if msg['Sender'].lower() == "assistant" else (child_name if msg['Sender'].lower() == "user" else msg['Sender'].capitalize())
                        formatted_timestamp = msg['Timestamp'].replace('T', ', ')
                        st.write(f"**{sender_display}:** {msg['Text']} ({formatted_timestamp})")
                else:
                    st.write("No messages in this session.")
                # Feedback section
                rating = session.get('rating', 0)
                feedback = session.get('feedback', '')
                if rating == 0:
                    st.markdown("**Rate this session:**")
                    selected = st.feedback("stars", key=f"rating_{session['session_id']}")
                    if selected is not None:
                        new_rating = selected + 1  # 0 -> 1 star, 1 -> 2 stars, etc.
                        new_feedback = st.text_area("Feedback (optional):", key=f"feedback_{session['session_id']}")
                        if st.button("Submit Feedback", key=f"submit_{session['session_id']}", use_container_width=True, type="primary"):
                            from database.sessions import update_session_feedback
                            update_session_feedback(session['session_id'], new_rating, new_feedback if new_feedback else None)
                            st.success("Feedback submitted!")
                            st.rerun()
                else:
                    st.write(f"**Your Rating:** {'⭐' * int(rating)}")
                    if feedback:
                        st.write(f"**Your Feedback:** {feedback}")
        else:
            st.write("No sessions for this child.")
    else:
        st.write("No children registered yet.")


render_footer()
