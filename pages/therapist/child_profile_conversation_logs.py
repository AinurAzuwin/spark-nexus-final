import streamlit as st
from streamlit_option_menu import option_menu
from database.children import get_children_by_therapist, assign_therapist_to_child, get_children_by_parent
from database.sessions import get_sessions_by_therapist, get_sessions_by_child
from database.messages import get_messages_by_session
from database.users import get_all_users, get_user_by_id
import uuid
from datetime import datetime, date
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
from datetime import datetime

def has_markdown(text):
    """Check if the text contains markdown elements."""
    if not text:
        return False
    # Common markdown indicators
    markdown_indicators = ['**', '*', '_', '`', '[', ']', '(', ')', '#', '##', '###', '-', '+', '1.', '2.', '3.']
    return any(indicator in text for indicator in markdown_indicators)

def calculate_age(dob_str):
    """Calculate age from date of birth string."""
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return "Unknown"

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
    <h2 style="margin: 0;">Child Profiles and Conversation Logs</h2>
    <p style="margin: 0;">Manage assigned children and view session logs.</p>
</div>
""", unsafe_allow_html=True)

# Display notifications if any
if 'notification' in st.session_state:
    if st.session_state['notification']['type'] == 'success':
        st.success(st.session_state['notification']['message'])
    elif st.session_state['notification']['type'] == 'error':
        st.error(st.session_state['notification']['message'])
    del st.session_state['notification']

therapist_id = st.session_state.get('user_id')

selected = option_menu(
    menu_title=None,
    options=["Assigned Children", "Register New Child", "Session Logs"],
    icons=["bi-person-circle", "bi-person-plus", "bi-chat-dots"],
    default_index=0,
    orientation="horizontal",
)

if selected == "Assigned Children":
    children = get_children_by_therapist(therapist_id)
    if children:
        for child in children:
            age = calculate_age(child['DOB'])
            with st.expander(f"{child['Name']} (Age: {age})"):
                parent = get_user_by_id(child['ParentID'])
                st.write(f"Parent Name: {parent['FullName'] if parent else 'Unknown'}")
                st.write(f"Parent Phone Number: {parent.get('ContactNumber', 'Unknown') if parent else 'Unknown'}")
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
                    st.write(f"**Therapist ID:** {child.get('TherapistID', 'Unknown')}")
                    st.write(f"**Therapist Name:** {child.get('TherapistName', 'Unknown')}")
                    if st.button("Close Details", key=f"close_{child['ChildID']}", use_container_width=True, type="primary"):
                        del st.session_state['selected_child']
                        st.rerun()
    else:
        st.write("No children assigned yet.")
elif selected == "Register New Child":
    all_users = get_all_users()
    parents = [u for u in all_users if u['UserRole'] == 'PARENT']
    if parents:
        st.markdown("<h4>Register New Child</h4>", unsafe_allow_html=True)
        form_counter = st.session_state.get('form_counter', 0)
        with st.form(f"register_child_{form_counter}"):
            parent_options = {u['FullName']: u['UserID'] for u in parents}
            st.markdown("**Select Parent:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
            selected_parent_name = st.selectbox("", list(parent_options.keys()), label_visibility="collapsed", key=f"select_parent_{form_counter}")
            st.markdown("**Child Name:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
            child_name = st.text_input("", label_visibility="collapsed", key=f"child_name_{form_counter}")
            st.markdown("**IC Number:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
            child_ic_number = st.text_input("", label_visibility="collapsed", key=f"child_ic_number_{form_counter}")
            st.markdown("**Gender:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
            child_gender = st.radio("", ['Male', 'Female'], horizontal=True, label_visibility="collapsed", key=f"child_gender_{form_counter}").upper()
            today = date.today()
            min_dob = today.replace(year=today.year - 7)
            max_dob = today.replace(year=today.year - 4)
            st.markdown("**Date of Birth:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
            child_dob = st.date_input("", min_value=min_dob, max_value=max_dob, label_visibility="collapsed", key=f"child_dob_{form_counter}")
            st.markdown("**Language Background:** <span style='color:red;'>*</span>", unsafe_allow_html=True)
            child_language = st.selectbox("", ["English", "Malay", "Mandarin", "Hokkien", "Cantonese", "Hakka", "Tamil", "Malayalam", "Telugu", "Iban", "Kadazan Dusun"], label_visibility="collapsed", key=f"child_language_{form_counter}")
            #st.markdown("**Diagnosis (Optional)**", unsafe_allow_html=True)
            st.divider()
            submitted = st.form_submit_button("Assign Child", use_container_width=True, type="primary")
            if submitted:
                if not child_name or not child_ic_number or not child_language:
                    st.session_state['notification'] = {'type': 'error', 'message': "Child Name, IC Number, and Language Background are required."}
                    st.rerun()
                else:
                    selected_parent_id = parent_options[selected_parent_name]
                    existing_children = get_children_by_parent(selected_parent_id)
                    if len(existing_children) >= 5:
                        st.session_state['notification'] = {'type': 'error', 'message': "This parent already has the maximum of 5 children. Cannot assign more."}
                        st.rerun()
                    else:
                        from database.children import create_child
                        child_id = str(uuid.uuid4())
                        create_child(child_id, child_name, str(child_dob), selected_parent_id, child_gender, child_language, "", child_ic_number, therapist_id, registration_date=datetime.utcnow().isoformat())
                        assign_therapist_to_child(child_id, therapist_id, st.session_state.get('full_name'))
                        # Clear form fields
                        for key in ['child_name', 'child_ic_number', 'child_gender', 'child_dob', 'child_language']:
                            if key in st.session_state:
                                del st.session_state[key]
                        # Increment form counter to reset the form
                        st.session_state['form_counter'] = st.session_state.get('form_counter', 0) + 1
                        st.session_state['notification'] = {'type': 'success', 'message': "Child assigned!"}
                        st.rerun()
    else:
        st.write("No parents available.")
elif selected == "Session Logs":
    children = get_children_by_therapist(therapist_id)
    if children:
        # Group children by parent
        parent_dict = {}
        for child in children:
            parent_id = child['ParentID']
            if parent_id not in parent_dict:
                parent_dict[parent_id] = {'parent': get_user_by_id(parent_id), 'children': []}
            parent_dict[parent_id]['children'].append(child)

        parent_options = {f"{data['parent']['FullName']}": pid for pid, data in parent_dict.items()}
        selected_parent_name = st.selectbox("Select Parent:", list(parent_options.keys()), key="parent_select")
        selected_parent_id = parent_options[selected_parent_name]

        child_options = {f"{child['Name']} (Age: {calculate_age(child['DOB'])})": child['ChildID'] for child in parent_dict[selected_parent_id]['children']}
        selected_child_name = st.selectbox("Select Child:", list(child_options.keys()), key="child_select")
        child_name = selected_child_name.split(' (Age:')[0]  # Extract child name
        selected_child_id = child_options[selected_child_name]

        sessions = get_sessions_by_child(selected_child_id)
        if sessions:
            # Sort sessions by session_number
            sessions_sorted = sorted(sessions, key=lambda s: s['session_number'])
            # Create display numbers starting from 1
            display_numbers = list(range(1, len(sessions_sorted) + 1))
            session_options = {f"Session {display_number}": session for display_number, session in zip(display_numbers, sessions_sorted)}
            selected_session_name = st.selectbox("Select Session:", list(session_options.keys()), key="session_select")
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
                # Show feedback
                rating = session.get('rating', 0)
                feedback = session.get('feedback', '')
                if rating:
                    st.write(f"**Parent Rating:** {'⭐' * int(rating)}")
                else:
                    st.write("**Parent Rating:** Not rated yet")
                if feedback:
                    st.write(f"**Parent Feedback:** {feedback}")
                else:
                    st.write("**Parent Feedback:** No feedback provided")
        else:
            st.write("No sessions for this child.")
    else:
        st.write("No children assigned yet.")
    
render_footer()
