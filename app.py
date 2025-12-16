import streamlit as st
import sys
import os
from dotenv import load_dotenv

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide")

load_dotenv()

# --- CRITICAL FIX: Add project root to sys.path ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

# --- IMPORTS ---
from database.users import authenticate_user_service, register_new_user
from utils.session_state import set_logged_in_session, get_logged_in_from_cookies
from utils.ui_components import render_footer
from streamlit_cookies_manager.encrypted_cookie_manager import EncryptedCookieManager

# --- COOKIE SETUP ---
cookies = EncryptedCookieManager(
    prefix="talktrack/",
    password="super_secret_cookie_key_123"
)
if not cookies.ready():
    st.stop()

st.session_state['cookies'] = cookies

cookie_data = get_logged_in_from_cookies(cookies)
if cookie_data:
    st.session_state.update(cookie_data)
else:
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "show_initial_landing" not in st.session_state:
        st.session_state["show_initial_landing"] = True

# --- LOGIN / SIGNUP FUNCTIONS ---
def render_login_tab():
    st.subheader("Login to your Account")

    # Display login error if any
    if 'login_error' in st.session_state:
        st.error(st.session_state['login_error'])
        del st.session_state['login_error']

    with st.form("generic_login_form"):
        st.markdown("Email <span style='color:red;'>*</span>", unsafe_allow_html=True)
        email = st.text_input("", key="login_Email_tab", label_visibility="collapsed").lower()
        st.markdown("Password <span style='color:red;'>*</span>", unsafe_allow_html=True)
        password = st.text_input("", type="password", key="login_Password_tab", label_visibility="collapsed")
        st.divider()
        submitted = st.form_submit_button("Log In", type="primary", key="login_pulse", use_container_width=True)

        if submitted:
            if not email or not password:
                st.session_state['login_error'] = "Please enter both email and password."
                st.rerun()

            user_data, error = authenticate_user_service(email, password)
            if user_data:
                if user_data.get('UserRole') == 'THERAPIST' and not user_data.get('Approved', False):
                    st.session_state['login_error'] = "Login failed: Therapist account pending approval."
                    st.rerun()

                set_logged_in_session(user_data, cookies)
                st.rerun()
            else:
                st.session_state['login_error'] = error
                st.rerun()
render_footer()

def render_signup_tab():
    # Display notifications if any
    if 'signup_notification' in st.session_state:
        if st.session_state['signup_notification']['type'] == 'success':
            st.success(st.session_state['signup_notification']['message'])
        elif st.session_state['signup_notification']['type'] == 'error':
            st.error(st.session_state['signup_notification']['message'])
        del st.session_state['signup_notification']

    st.subheader("Create a New Account")
    form_counter = st.session_state.get('signup_form_counter', 0)
    with st.form(f"register_form_{form_counter}"):
        new_role = st.radio(
            "I am registering as a:",
            ['Parent', 'Therapist'],
            key=f'signup_role_select_{form_counter}',
            index=0,
            horizontal=True
        ).upper()

        st.markdown("Full Name <span style='color:red;'>*</span>", unsafe_allow_html=True)
        new_name = st.text_input("", key=f'signup_name_{form_counter}', label_visibility="collapsed")
        st.markdown("Email <span style='color:red;'>*</span>", unsafe_allow_html=True)
        new_email = st.text_input("", key=f'signup_email_{form_counter}', label_visibility="collapsed").lower()
        st.markdown("Contact Number <span style='color:red;'>*</span>", unsafe_allow_html=True)
        new_contact = st.text_input("", key=f'signup_contact_{form_counter}', label_visibility="collapsed")
        license_id = None
        if new_role == 'THERAPIST':
            st.markdown("Professional License/Registration ID <span style='color:red;'>*</span>", unsafe_allow_html=True)
            license_id = st.text_input("", help="Required for verification by Admin.", key=f'signup_license_{form_counter}', label_visibility="collapsed")
            st.info("Therapist accounts must be approved by Admin before login.")

        st.markdown("Password <span style='color:red;'>*</span>", unsafe_allow_html=True)
        new_password = st.text_input("", type="password", key=f'signup_password_{form_counter}', label_visibility="collapsed")
        st.markdown("Confirm Password <span style='color:red;'>*</span>", unsafe_allow_html=True)
        confirm_password = st.text_input("", type="password", key=f'signup_confirm_{form_counter}', label_visibility="collapsed")
        st.divider()
        submitted = st.form_submit_button("Create Account", type="primary", key=f"signup_pulse_{form_counter}", use_container_width=True)

        if submitted:
            if not new_name or not new_email or not new_contact:
                st.session_state['signup_notification'] = {'type': 'error', 'message': "Full Name, Email, and Contact Number are required."}
                st.rerun()
            if new_password != confirm_password:
                st.session_state['signup_notification'] = {'type': 'error', 'message': "Passwords do not match."}
                st.rerun()
            if len(new_password) < 6:
                st.session_state['signup_notification'] = {'type': 'error', 'message': "Password must be at least 6 characters."}
                st.rerun()
            if new_role == 'THERAPIST' and not license_id:
                st.session_state['signup_notification'] = {'type': 'error', 'message': "License/Registration ID is required for Therapist registration."}
                st.rerun()

            result = register_new_user(new_email, new_password, new_role, new_name, new_contact, license_id=license_id)

            if result is True:
                msg = "Registration complete! Therapist account pending approval." if new_role == 'THERAPIST' \
                      else "Registration successful! You can now log in."
                st.session_state['signup_notification'] = {'type': 'success', 'message': msg}
                st.session_state['signup_form_counter'] = form_counter + 1
                st.rerun()
            elif result == "User already exists":
                st.session_state['signup_notification'] = {'type': 'error', 'message': "This email is already registered."}
                st.rerun()
            else:
                st.session_state['signup_notification'] = {'type': 'error', 'message': "Registration failed. Please check your data."}
                st.rerun()

def render_initial_landing_page():
    # Hide sidebar on initial landing page
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.set_page_config(
        page_title="Halo Child",
        page_icon=":material/voice_selection:",
        layout="wide",
    )

    # Load custom CSS
    with open("assets/styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    st.image("assets/spark-nexus.png", use_container_width=True)

    col_left, col_right = st.columns([2, 3])

    with col_left:
        st.image("assets/kid_speak.png", use_container_width=True)

    with col_right:
        st.markdown('<h1 class="welcome-title">Welcome to Halo Child</h1>', unsafe_allow_html=True)
        st.write(
            "Halo Child offers a safe and engaging environment for children, "
            "supporting speech practice while assisting therapists with insightful progress tracking. "
            "Explore interactive sessions, monitor wellbeing, and make learning both fun and meaningful! 🎉"
        )

        if st.button(
            "Get Started", 
            key="get_started", 
            help="Click to begin your journey!", 
            type="primary", 
            use_container_width=True
        ):
            st.session_state["show_initial_landing"] = False
            st.session_state["show_balloons"] = True
            st.rerun()

    st.divider()

    with st.expander("🔍 Learn more about how it works"):
        st.markdown('<div class="expander-content">', unsafe_allow_html=True)
        st.write(
            "Halo Child is designed for children with autism to support speech screening "
            "and therapy sessions. It helps identify potential language delays, normal progress, "
            "or attention-related conditions such as ADHD. "
            "Our integrated system combines interactive robotics, AI assistance, wearable emotion monitoring, "
            "and automated reporting to assist therapists while keeping sessions engaging and insightful for children."
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("Why Halo Child?")
    f1, f2, f3, f4 = st.columns(4)
    
    # Feature cards
    with f1:
        st.markdown(
            '<div class="feature-card"><div class="feature-icon"><i class="material-icons">smart_toy</i></div>'
            '<h3>Simba Robot</h3>'
            '<p>An interactive companion that engages children during speech sessions, '
            'encouraging independent practice without constant therapist involvement.</p>'
            '</div>', unsafe_allow_html=True
        )
    with f2:
        st.markdown(
            '<div class="feature-card"><div class="feature-icon"><i class="material-icons">chat</i></div>'
            '<h3>AI Assistant</h3>'
            '<p>Smart AI agent guides conversations and responds to children, '
            'making practice adaptive and personalized.</p>'
            '</div>', unsafe_allow_html=True
        )
    with f3:
        st.markdown(
            '<div class="feature-card"><div class="feature-icon"><i class="material-icons">watch</i></div>'
            '<h3>EmotiBit</h3>'
            '<p>Monitors heart rate, emotional state, and engagement levels, '
            'providing valuable insights during sessions.</p>'
            '</div>', unsafe_allow_html=True
        )
    with f4:
        st.markdown(
            '<div class="feature-card"><div class="feature-icon"><i class="material-icons">description</i></div>'
            '<h3>Auto NLP Reports</h3>'
            '<p>Generates detailed session reports automatically, '
            'reducing therapist workload while keeping parents informed.</p>'
            '</div>', unsafe_allow_html=True
        )

def render_landing_page():
    # Hide sidebar on login page
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Show balloons if triggered
    if st.session_state.get('show_balloons', False):
        st.balloons()
        st.session_state['show_balloons'] = False

    # Add Spark-Nexus logo header
    st.image("assets/spark-nexus.png", width=780)
    st.title("Welcome to Halo Child")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    with login_tab:
        render_login_tab()
    with signup_tab:
        render_signup_tab()
    render_footer()

# --- MAIN LOGIC ---
if st.session_state.get('logged_in', False):

    # --- LOGO ---
    st.logo("assets/advantech.png", size="large")

    # Make logo bigger
    st.markdown(
        """
        <style>
        img {
            width: 180px !important;
            height: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    role = st.session_state['user_role']

    if role == 'PARENT':
        # Use st.navigation for multipage app with sections
        pg = st.navigation({
            "Dashboard": [
                st.Page("pages/parent/main_dashboard.py", title="Main Dashboard", icon=":material/dashboard:"),
                st.Page("pages/parent/wise_paas_dashboard.py", title="Wise-PaaS Dashboard", icon=":material/analytics:"),
            ],
            "Child Management": [
                st.Page("pages/parent/child_conversation.py", title="Children & Conversations", icon=":material/child_care:"),
                st.Page("pages/parent/appointments.py", title="Appointments", icon=":material/calendar_today:"),
                st.Page("pages/parent/report_notes.py", title="Session Reports", icon=":material/news:"),
            ],
        })
        pg.run()
    elif role == 'THERAPIST':
        # Use st.navigation for multipage app with sections
        pg = st.navigation({
            "Dashboard": [
                st.Page("pages/therapist/main_dashboard.py", title="Main Dashboard", icon=":material/dashboard:"),
                st.Page("pages/therapist/wise_paas_dashboard_realtime.py", title="Wise-PaaS Dashboard", icon=":material/analytics:"),
            ],
            "Child Management": [
                st.Page("pages/therapist/child_profile_conversation_logs.py", title="Child and Conversation", icon=":material/escalator_warning:"),
                st.Page("pages/therapist/ai_agent.py", title="AI Agent", icon=":material/robot_2:"),
            ],
            "Approval": [
                st.Page("pages/therapist/report_note_approval.py", title="Report and Note", icon=":material/clinical_notes:"),
                st.Page("pages/therapist/appointment_approval.py", title="Appointment", icon=":material/calendar_check:"),
            ],
        })
        pg.run()
    elif role == 'ADMIN':
        # Use st.navigation for multipage app with sections
        pg = st.navigation({
            "Dashboard": [
                st.Page("pages/admin/analytics_overview.py", title="Analytics Overview", icon=":material/finance_mode:"),
            ],
            "Management": [
                st.Page("pages/admin/user_management.py", title="User", icon=":material/group:"),
                st.Page("pages/admin/data_management.py", title="Data", icon=":material/data_table:"),
            ],
            "Notification": [
                st.Page("pages/admin/assignment.py", title="Assignment", icon=":material/assignment_ind:"),
                st.Page("pages/admin/therapist_approval.py", title="Therapist Approval", icon=":material/assignment_turned_in:"),
            ],
        })
        pg.run()

else:
    if st.session_state.get('show_initial_landing', True):
        render_initial_landing_page()
    else:
        render_landing_page()
