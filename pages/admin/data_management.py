import streamlit as st
from streamlit_option_menu import option_menu
import boto3
import os
import pandas as pd
from utils.session_state import clear_cookies
from utils.ui_components import render_footer
from dotenv import load_dotenv
from datetime import datetime, date

# -----------------------------
# Load AWS credentials
# -----------------------------
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")

# Initialize DynamoDB
dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Tables
sessions_table = dynamodb.Table("sessions")
reports_table = dynamodb.Table("reports")
children_table = dynamodb.Table("children")
users_table = dynamodb.Table("users")
messages_table = dynamodb.Table("messages")

# -----------------------------
# Logout function
# -----------------------------
def logout():
    clear_cookies(st.session_state.get("cookies"))
    keys_to_clear = ["logged_in", "user_id", "user_role", "full_name", "user_email"]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    st.rerun()

# -----------------------------
# Helper functions
# -----------------------------
def calculate_age(dob_str):
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return "Unknown"

def format_timestamp(ts_str):
    """Format timestamp to YYYY-MM-DD HH:MM:SS.xx"""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-4]
    except:
        return ts_str

# -----------------------------
# Sidebar logout button
# -----------------------------
with st.sidebar:
    if st.button(
        "Logout",
        icon=":material/logout:",
        help="Click to securely log out",
        use_container_width=True,
    ):
        logout()

# -----------------------------
# Page Header
# -----------------------------
st.markdown(
    """
    <style>
        .safe-header {
            background-color: #004280;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .filter-box {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .filter-title {
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        .dataframe th {
            background-color: #004280 !important;
            color: white !important;
            text-align: center !important;
        }
        .dataframe td {
            text-align: center;
            padding: 6px;
        }
    </style>
""",
    unsafe_allow_html=True,
)
st.markdown(
    """
<div class="safe-header">
    <h2 style="margin: 0;">Data Management</h2>
    <p style="margin: 0;">Manage system data and view conversation logs.</p>
</div>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# Tabs
# -----------------------------
selected_tab = option_menu(
    menu_title=None,
    options=["Report Status", "Conversation Logs"],
    icons=["bi-file-earmark-text", "bi-chat-dots"],
    default_index=0,
    orientation="horizontal",
)

# -----------------------------
# Report Status Tab
# -----------------------------
if selected_tab == "Report Status":
    try:
        reports_response = reports_table.scan()
        reports = reports_response.get("Items", [])

        display_data = []
        for report in reports:
            child_id = report.get("ChildID")
            session_id = report.get("SessionID")

            child_info = children_table.get_item(Key={"ChildID": child_id}).get("Item", {})
            session_info = sessions_table.get_item(Key={"session_id": session_id}).get("Item", {})

            parent_name = "N/A"
            parent_id = child_info.get("ParentID")
            if parent_id:
                parent_info = users_table.get_item(Key={"UserID": parent_id}).get("Item")
                if parent_info:
                    parent_name = parent_info.get("FullName", "N/A")

            display_data.append({
                "Approval Status": "✅" if report.get("Approved") else "❌",
                "Child Name": child_info.get("Name"),
                "Parent Name": parent_name,
                "Session Number": session_info.get("session_number"),
                "Therapist Name": child_info.get("TherapistName"),
                "Diagnosis": child_info.get("Diagnosis"),
                "Gender": child_info.get("Gender"),
                "DOB": child_info.get("DOB"),
            })

        if display_data:
            df = pd.DataFrame(display_data)
            st.markdown('<div class="filter-title">Filters</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 2])

            with col1:
                approval_filter = st.multiselect(
                    "Approval Status", options=["✅", "❌"], default=["✅", "❌"]
                )
            with col2:
                therapist_filter = st.text_input("Therapist Name (partial match)")
            with col3:
                child_filter = st.text_input("Child Name (partial match)")

            filtered_df = df[df["Approval Status"].isin(approval_filter)]
            if therapist_filter:
                filtered_df = filtered_df[filtered_df["Therapist Name"].str.contains(therapist_filter, case=False)]
            if child_filter:
                filtered_df = filtered_df[filtered_df["Child Name"].str.contains(child_filter, case=False)]

            st.dataframe(
                filtered_df.style.set_properties(**{
                    "border": "none",
                    "padding": "6px",
                    "text-align": "center"
                }).set_table_styles([
                    {'selector': 'th', 'props': [('background-color', '#004280'), ('color', 'white'), ('text-align', 'center')]},
                    {'selector': 'td:nth-child(4)', 'props': [('text-align', 'center')]}  
                ]).hide(axis="index"),
                use_container_width=True
            )
        else:
            st.info("No reports found in the database.")

    except Exception as e:
        st.error(f"Error fetching data from DynamoDB: {e}")

# -----------------------------
# Conversation Logs Tab
# -----------------------------
elif selected_tab == "Conversation Logs":

    try:
        all_users = users_table.scan().get("Items", [])
        therapists = [u for u in all_users if u.get("UserRole") == "THERAPIST" and u.get("Approved", False)]
        therapist_options = {t["FullName"]: t["UserID"] for t in therapists}

        if therapist_options:
            selected_therapist_name = st.selectbox("Select Therapist:", list(therapist_options.keys()))
            selected_therapist_id = therapist_options[selected_therapist_name]

            children = children_table.scan().get("Items", [])
            parents_under_therapist = {}
            for child in children:
                if child.get("TherapistID") == selected_therapist_id:
                    parent_id = child.get("ParentID")
                    if parent_id and parent_id not in parents_under_therapist:
                        parent_info = users_table.get_item(Key={"UserID": parent_id}).get("Item")
                        if parent_info:
                            parents_under_therapist[parent_info["FullName"]] = parent_id

            if parents_under_therapist:
                selected_parent_name = st.selectbox("Select Parent:", list(parents_under_therapist.keys()))
                selected_parent_id = parents_under_therapist[selected_parent_name]

                child_options = {}
                for child in children:
                    if child.get("ParentID") == selected_parent_id and child.get("TherapistID") == selected_therapist_id:
                        age = calculate_age(child.get("DOB"))
                        child_options[f"{child.get('Name')} (Age: {age})"] = child.get("ChildID")

                if child_options:
                    selected_child_name = st.selectbox("Select Child:", list(child_options.keys()))
                    selected_child_id = child_options[selected_child_name]

                    sessions = sessions_table.scan().get("Items", [])
                    sessions_for_child = [s for s in sessions if s.get("child_id") == selected_child_id]

                    if sessions_for_child:
                        # Use session number for selection
                        session_options = {f"Session {s.get('session_number', s['session_id'])}": s['session_id'] for s in sorted(sessions_for_child, key=lambda x: x.get('session_number', x['session_id']), reverse=True)}
                        selected_session_name = st.selectbox("Select Session:", list(session_options.keys()))
                        selected_session_id = session_options[selected_session_name]

                        messages = messages_table.scan().get("Items", [])
                        messages_for_session = [m for m in messages if m.get("session_id") == selected_session_id]
                        messages_for_session.sort(key=lambda x: x.get("timestamp"))

                        if messages_for_session:
                            st.subheader("Conversation Logs")
                            child_actual_name = selected_child_name.split(" (")[0]  # Extract child name
                            for msg in messages_for_session:
                                role = msg.get("role", "Unknown")
                                if role.lower() == "assistant":
                                    role_display = "AI Agent"
                                else:
                                    role_display = child_actual_name
                                timestamp = format_timestamp(msg.get("timestamp", ""))
                                content = msg.get("content", "")
                                st.markdown(f"*{role_display} ({timestamp}):* {content}")
                        else:
                            st.info("No messages in this session.")
                    else:
                        st.info("No sessions for this child.")
                else:
                    st.info("No children under this parent for this therapist.")
            else:
                st.info("No parents associated with this therapist.")
        else:
            st.info("No therapists found.")

    except Exception as e:
        st.error(f"Error fetching conversation logs: {e}")

# -----------------------------
# Footer
# -----------------------------
render_footer()