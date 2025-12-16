"""
Unified Clinical Language Screening Interface
Single app that opens child interface automatically
UPDATED: Greeting starts only when child interface is ready
INTEGRATED: Nexus Hardware Controller (Eye Tracking/Emotion AI)
FIXED: Reopen Child Window button restored
"""
import sys
import os
import streamlit as st

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from system_config import AppConfig

# AUTO-START CHILD VIEW (only in development)
if 'child_view_started' not in st.session_state:
    st.session_state.child_view_started = False
    AppConfig.start_child_view()
    st.session_state.child_view_started = True


# Get the directory where THIS file (ai_agent.py) is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add that directory to Python's search path
sys.path.insert(0, current_dir)  # <--- insert(0) puts it at the FRONT of the line

import streamlit as st
from llm_agent import LanguageScreeningAgent
from audio_handler import AudioHandler
from database_handler import DatabaseHandler
import agent_settings
import base64
import uuid
import time
import re
import paramiko # Added for Hardware Control
from datetime import datetime
import streamlit.components.v1 as components
from robot_controller import RobotController
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

# -----------------------------
# 🔒 NEXUS CONFIGURATION
# -----------------------------
RPI_IP = "10.218.53.90"   # <--- UPDATE THIS
RPI_USER = "pi"
RPI_PASS = "emoti1234"   # <--- UPDATE THIS

# PATHS
PATH_SRC = "/usr/src/Python-3.9.18"
ENV_SRC = "mp_env"
PATH_EMO = "/home/pi/emotion"
ENV_EMO = "venv"

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(180deg, #E8F4F8 0%, #F0F8FF 100%);
        overflow: hidden !important; /* Hide main page scrollbar */
    }
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0rem !important;
        max-width: 100vw !important;
    }
    .stChatMessage {
        font-size: 1.3em;
        border-radius: 15px;
        margin: 10px 0;
    }
    /* Hide footer in AI Agent page */
    footer {
        display: none !important;
    }
    footer:after {
        content: none !important;
    }
    h1 {
        color: #2C5F7C;
        font-size: 2.5em !important;
        text-align: center;
    }
    /* 2. COLUMN LAYOUT - CRITICAL FOR SCROLLING */
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
        gap: 2rem !important;
    }

    /* LEFT COLUMN (Chat) - SCROLLABLE */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child {
        height: calc(100vh - 120px) !important; /* Fixed height triggers internal scroll */
        overflow-y: auto !important;
        overflow-x: hidden !important;
        padding-right: 15px !important;
        scroll-behavior: smooth !important;
        display: flex;
        flex-direction: column;
    }

    /* RIGHT COLUMN (Controls) - FIXED/SEPARATE */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
        height: calc(100vh - 120px) !important;
        overflow-y: auto !important;
    }

    /* Custom Scrollbar Styling */
    div[data-testid="stColumn"]::-webkit-scrollbar {
        width: 8px;
    }
    div[data-testid="stColumn"]::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    div[data-testid="stColumn"]::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 10px;
    }
    div[data-testid="stColumn"]::-webkit-scrollbar-thumb:hover {
        background: #5568d3;
    }

    /* 3. COMPONENT STYLES */
    .stChatMessage {
        font-size: 1.1em;
        border-radius: 15px;
        margin: 10px 0;
        background-color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #E1E4E8;
    }
    
    h1 {
        color: #2C5F7C;
        font-size: 2.2em !important;
        text-align: center;
        margin-bottom: 20px !important;
    }
    .child-window-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 30px;
        border-radius: 10px;
        font-size: 1.2em;
        font-weight: bold;
        text-align: center;
        cursor: pointer;
        border: none;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    .child-window-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    /* === NEW: Enhanced Selectbox Styling === */
    
    /* Make the selectbox label bold and bigger */
    div[data-testid="stSelectbox"] label {
        font-weight: 700 !important;
        font-size: 1.1em !important;
        color: #2C5F7C !important;
        margin-bottom: 8px !important;
    }
    
    /* Style the selectbox container */
    div[data-testid="stSelectbox"] > div > div {
        border: 2px solid #667eea !important;
        border-radius: 10px !important;
        background-color: white !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.15) !important;
        transition: all 0.3s ease !important;
    }
    
    /* Hover effect on selectbox */
    div[data-testid="stSelectbox"] > div > div:hover {
        border-color: #764ba2 !important;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
        transform: translateY(-1px);
    }
    /* === NEW: Conversation Column Scrolling === */
    /* Hide the main page scrollbar */
    section.main {
        overflow: hidden !important;
    }

    /* Target the chat column specifically */
    div[data-testid="column"]:first-child {
        overflow-y: auto !important;
        overflow-x: hidden !important;
        max-height: calc(100vh - 100px) !important;
        padding-right: 10px !important;
        scroll-behavior: smooth !important;
    }

    /* Custom scrollbar for conversation column */
    div[data-testid="column"]:first-child::-webkit-scrollbar {
        width: 8px;
    }

    div[data-testid="column"]:first-child::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }

    div[data-testid="column"]:first-child::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 10px;
    }

    div[data-testid="column"]:first-child::-webkit-scrollbar-thumb:hover {
        background: #5568d3;
    }
    /* Make selected text bold and bigger */
    div[data-testid="stSelectbox"] input {
        font-weight: 600 !important;
        font-size: 1.05em !important;
        color: #2C3E50 !important;
    }
    
    /* Style the dropdown arrow */
    div[data-testid="stSelectbox"] svg {
        color: #667eea !important;
        width: 24px !important;
        height: 24px !important;
    }
    /* Nexus Health Status Styles */
    .health-card { background-color: white; padding: 10px; border-radius: 8px; margin-bottom: 5px; border-left: 4px solid #ccc; font-size: 12px;}
    .health-running { border-left-color: #27AE60; }
    .health-stopped { border-left-color: #C0392B; }
    
    /* Calibration Styles */
    .calib-card {
        background-color: white; 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .instruction-big { font-size: 24px; font-weight: bold; color: #2C3E50; margin-bottom: 10px; }
    .instruction-small { font-size: 16px; color: #7F8C8D; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# NEXUS HARDWARE FUNCTIONS
# -----------------------------
def get_ssh_client():
    if 'ssh_client' not in st.session_state: st.session_state.ssh_client = None
    return st.session_state.ssh_client

def connect_ssh():
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(RPI_IP, username=RPI_USER, password=RPI_PASS, timeout=5)
        st.session_state.ssh_client = client
        st.session_state.is_connected = True
        return True
    except Exception as e:
        st.error(f"Hardware Connection Failed: {e}")
        return False

def run_bg(client, cmd, log_file):
    """Runs command using nohup and bash -c to ensure environment loads"""
    wrapped_cmd = f"nohup bash -c '{cmd}' > {log_file} 2>&1 &"
    client.exec_command(wrapped_cmd)

def check_process_status(client, process_name, log_file):
    """Checks if a process is running and reads the last line of its log"""
    try:
        stdin, stdout, stderr = client.exec_command(f"pgrep -f {process_name}")
        pid = stdout.read().decode().strip()
        is_running = len(pid) > 0
        
        stdin, stdout, stderr = client.exec_command(f"tail -n 3 {log_file}")
        log_lines = stdout.read().decode().strip()
        if not log_lines: log_lines = "No logs yet..."
        
        return is_running, log_lines
    except:
        return False, "Connection Error"

# -----------------------------
# APP LOGIC
# -----------------------------

def initialize_session():
    """Initialize session state with optimizations"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "audio_handler" not in st.session_state:
        st.session_state.audio_handler = AudioHandler()
        # PRE-LOAD common phrases for instant TTS on first use
        if agent_settings.ENABLE_TTS_CACHE:
            print("🚀 Pre-loading common TTS phrases...")
            st.session_state.audio_handler.preload_common_phrases()
    if "db_handler" not in st.session_state:
        st.session_state.db_handler = DatabaseHandler()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_started" not in st.session_state:
        st.session_state.conversation_started = False
    if "enable_stt" not in st.session_state:
        st.session_state.enable_stt = agent_settings.ENABLE_SPEECH_TO_TEXT
    if "enable_tts" not in st.session_state:
        st.session_state.enable_tts = agent_settings.ENABLE_TEXT_TO_SPEECH
    if "last_interaction_time" not in st.session_state:
        st.session_state.last_interaction_time = None
    if "audio_played_count" not in st.session_state:
        st.session_state.audio_played_count = 0
    if "children_list" not in st.session_state:
        st.session_state.children_list = []
    if "selected_child_id" not in st.session_state:
        st.session_state.selected_child_id = None
    if "selected_child_name" not in st.session_state:
        st.session_state.selected_child_name = None
    if "last_db_message_count" not in st.session_state:
        st.session_state.last_db_message_count = 0
    if "monitoring_mode" not in st.session_state:
        st.session_state.monitoring_mode = True
    if "child_window_opened" not in st.session_state:
        st.session_state.child_window_opened = False
    if "waiting_for_child_ready" not in st.session_state:
        st.session_state.waiting_for_child_ready = False
    if "greeting_sent" not in st.session_state:
        st.session_state.greeting_sent = False
    
    if "robot_controller" not in st.session_state:
        if agent_settings.ENABLE_ROBOT_ACTIONS:
            st.session_state.robot_controller = RobotController()
        else:
            st.session_state.robot_controller = None
    
    if "robot_enabled" not in st.session_state:
        st.session_state.robot_enabled = agent_settings.ENABLE_ROBOT_ACTIONS

    # --- NEXUS VARIABLES ---
    if "ssh_client" not in st.session_state: st.session_state.ssh_client = None
    if "is_connected" not in st.session_state: st.session_state.is_connected = False
    if "hardware_running" not in st.session_state: st.session_state.hardware_running = False
    if "calibration_step" not in st.session_state: st.session_state.calibration_step = 0
    if "last_hardware_status" not in st.session_state: st.session_state.last_hardware_status = "Waiting..."
    if "shell" not in st.session_state: st.session_state.shell = None

def load_children():
    """Load children list from database - filtered by therapist"""
    # Get the therapist ID from session state (set by your friend's login system)
    therapist_id = st.session_state.get('user_id', None)
    
    if not therapist_id:
        st.error("❌ User ID not found. Please log in again.")
        st.session_state.children_list = []
        return
    
    print(f"👨‍⚕️ Loading children for therapist: {therapist_id}")
    
    # Pass therapist_id to filter children
    st.session_state.children_list = st.session_state.db_handler.get_all_children(
        therapist_id=therapist_id
    )
    
    if not st.session_state.children_list:
        print(f"⚠️ No children found for therapist {therapist_id}")
    else:
        print(f"✅ Loaded {len(st.session_state.children_list)} children for therapist {therapist_id}")

def open_child_window():
    """
    Opens child interface - works in both development and production
    Development: Opens http://localhost:8502
    Production: Opens ?mode=child on same domain
    """
    child_url = AppConfig.get_child_url()
    
    if AppConfig.is_production():
        # Production: relative URL with query param
        js_code = f"""
        <script>
            (function() {{
                var baseUrl = window.location.origin + window.location.pathname;
                var childUrl = baseUrl + '{child_url}';
                
                console.log('🚀 Opening child window (PRODUCTION):', childUrl);
                
                var popup = window.open(
                    childUrl,
                    'ChildInterface',
                    'width=800,height=600,left=100,top=100'
                );
                
                if (!popup || popup.closed || typeof popup.closed == 'undefined') {{
                    alert('⚠️ Pop-up blocked! Please allow pop-ups and try again.\\n\\nOr visit: ' + childUrl);
                }}
            }})();
        </script>
        """
    else:
        # Development: absolute URL with port
        js_code = f"""
        <script>
            (function() {{
                var childUrl = '{child_url}';
                
                console.log('🚀 Opening child window (DEVELOPMENT):', childUrl);
                
                var popup = window.open(
                    childUrl,
                    'ChildInterface',
                    'width=800,height=600,left=100,top=100'
                );
                
                if (!popup || popup.closed || typeof popup.closed == 'undefined') {{
                    alert('⚠️ Pop-up blocked! Please allow pop-ups and try again.\\n\\nOr visit: ' + childUrl);
                }}
            }})();
        </script>
        """
    
    return components.html(js_code, height=0)

def sync_messages_from_db():
    """
    Sync messages from database - only for CURRENT session
    FIXED: Now syncs BOTH user and assistant messages with FULL DEBUG
    """
    if not st.session_state.session_id:
        print("⚠️ SYNC: No session_id - cannot sync")
        return False
    
    # ===== ADD THIS CHECK =====
    # Verify this session still exists and is active
    try:
        session = st.session_state.db_handler.get_session(st.session_state.session_id)
        if not session:
            print(f"❌ SYNC ERROR: Session {st.session_state.session_id} not found in database!")
            return False
        
        if session.get('status') != 'active':
            print(f"⚠️ SYNC WARNING: Session {st.session_state.session_id} is not active (status: {session.get('status')})")
            return False
        
        print(f"✅ Session {st.session_state.session_id} verified (status: active)")
    except Exception as e:
        print(f"❌ Session verification failed: {e}")
        return False
    # ===== END CHECK =====
    
    try:
        print(f"\n🔍 SYNC CHECK:")
        print(f"   Session ID: {st.session_state.session_id}")
        print(f"   Local message count: {len(st.session_state.messages)}")
        
        # Get all messages from database for current session
        db_messages = st.session_state.db_handler.get_session_messages(st.session_state.session_id)
        
        print(f"   DB message count: {len(db_messages)}")
        
        # Debug: Show what's in the database
        if db_messages:
            print(f"   📋 DB Messages:")
            for idx, msg in enumerate(db_messages):
                print(f"      {idx+1}. [{msg.get('role')}] {msg.get('content', '')[:40]}...")
        else:
            print(f"   ⚠️ No messages found in database!")
        
        # Get current local count
        current_local_count = len(st.session_state.messages)
        
        # Check if there are new messages in database
        if len(db_messages) > current_local_count:
            print(f"📥 SYNC: Found {len(db_messages) - current_local_count} new message(s)")
            
            # Get all new messages (not just the last one)
            new_messages = db_messages[current_local_count:]
            
            print(f"   🆕 New messages to sync:")
            for idx, msg in enumerate(new_messages):
                print(f"      {idx+1}. [{msg.get('role')}] {msg.get('content', '')[:50]}...")
            
            # Add each new message to local state
            messages_added = False
            for new_message in new_messages:
                # Check if message already exists (by content comparison)
                already_exists = any(
                    m.get('content') == new_message['content'] and 
                    m.get('role') == new_message['role']
                    for m in st.session_state.messages
                )
                
                if already_exists:
                    print(f"   ⏭️ Skipping duplicate: [{new_message['role']}] {new_message['content'][:30]}...")
                    continue
                
                # Prepare message data
                message_data = {
                    "role": new_message['role'],
                    "content": new_message['content']
                }
                
                # Add metadata for assistant messages
                if new_message['role'] == 'assistant':
                    metadata = new_message.get('metadata', {})
                    
                    # Extract robot action if present
                    if metadata.get('robot_action'):
                        message_data['robot_action'] = metadata['robot_action']
                    
                    # Extract emotion if present
                    if metadata.get('emotion'):
                        message_data['emotion'] = metadata['emotion']
                    
                    # Extract picture info if present
                    if metadata.get('picture_path'):
                        message_data['picture'] = {
                            'path': metadata.get('picture_path'),
                            'filename': metadata.get('picture_filename'),
                            'complexity': metadata.get('picture_complexity')
                        }
                
                # Add to local messages
                st.session_state.messages.append(message_data)
                messages_added = True
                
                print(f"   ✅ Added {new_message['role']} message: {new_message['content'][:50]}...")
            
            if messages_added:
                print(f"✅ SYNC: Successfully synced {len(new_messages)} message(s)")
                print(f"   Total local messages now: {len(st.session_state.messages)}")
                return True
            else:
                print(f"⚠️ SYNC: No new messages added (all duplicates)")
                return False
        else:
            print(f"   ℹ️ No new messages (DB: {len(db_messages)}, Local: {current_local_count})")
        
        return False
        
    except Exception as e:
        print(f"❌ Sync error: {e}")
        import traceback
        traceback.print_exc()
        return False

def start_conversation(child_id: str, clinician_id: str = None):
    """Start a new screening session AND Launch Nexus Hardware"""
    
    # 1. Get clinician_id from session state (MUST have valid user_id)
    if not clinician_id:
        clinician_id = st.session_state.get('user_id')
    
    if not clinician_id:
        st.error("❌ Clinician ID not found. Please log in again.")
        return False
    
    print(f"👨‍⚕️ Starting session with clinician_id: {clinician_id}")
    
    # 2. End any existing active sessions
    print(f"🔍 Checking for existing active sessions...")
    existing_sessions = st.session_state.db_handler.get_all_sessions(limit=50)
    for session in existing_sessions:
        if session.get('status') == 'active':
            print(f"⚠️ Found active session: {session.get('session_id')} - ending it")
            st.session_state.db_handler.end_session(session.get('session_id'))
    
    # 3. Generate new session ID
    st.session_state.session_id = f"session_{uuid.uuid4().hex[:12]}"
    print(f"🆕 Creating new session: {st.session_state.session_id}")
    
    # 4. Fetch child information
    child = st.session_state.db_handler.get_child(child_id)
    if not child:
        st.error("Child not found in database")
        return False
    
    st.session_state.selected_child_id = child_id
    st.session_state.selected_child_name = child.get('Name', child.get('name', 'Unknown'))
    
    # Calculate age
    child_age = None
    child_dob = child.get('DOB', child.get('date_of_birth', ''))
    
    if child_dob:
        try:
            dob = datetime.strptime(child_dob, '%Y-%m-%d')
            today = datetime.today()
            child_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        except:
            child_age = child.get('age')
    else:
        child_age = child.get('age')
    
    metadata = {
        'child_age': child_age,
        'date_of_birth': child_dob,
        'additional_info': child.get('additional_info', {}),
        'child_ready': False  # NEW: Flag to track when child interface is ready
    }
    
    # 5. Create session in database with proper clinician_id
    success = st.session_state.db_handler.create_session(
        st.session_state.session_id,
        child_id,
        clinician_id,  # This is now guaranteed to be the actual user_id from login
        metadata
    )
    
    if not success:
        st.error("Failed to create session in database")
        return False

    # 7. Reset Session State
    st.session_state.messages = []  # Clear local messages
    st.session_state.conversation_started = True
    st.session_state.last_interaction_time = time.time()
    st.session_state.last_db_message_count = 0
    st.session_state.child_window_opened = False
    st.session_state.audio_played_count = 0
    st.session_state.waiting_for_child_ready = True
    st.session_state.greeting_sent = True

    # --- 🚀 NEXUS HARDWARE LAUNCH SEQUENCE ---
    if st.session_state.get('is_connected', False):
        try:
            client = get_ssh_client()
            
            # Start MQTT Bridge
            cmd_mqtt = f"cd {PATH_SRC} && source {ENV_SRC}/bin/activate && python3 -u mqtt_to_dynamo.py"
            run_bg(client, cmd_mqtt, "/tmp/nexus_mqtt.log")
            
            # Start Emotion AI
            cmd_emo = f"cd {PATH_EMO} && source {ENV_EMO}/bin/activate && python3 -u rpi_emotion_detect.py"
            run_bg(client, cmd_emo, "/tmp/nexus_emo.log")
            
            # Start Eye Tracker Interactive Shell
            shell = client.invoke_shell()
            shell.send(f"cd {PATH_SRC} && source {ENV_SRC}/bin/activate && python3 -u eye.py\n")
            
            st.session_state.shell = shell
            st.session_state.hardware_running = True
            st.session_state.calibration_step = 1
            print("✅ Nexus Hardware Launched")
        except Exception as e:
            st.error(f"Hardware Launch Failed: {e}")
    else:
        print("⚠️ Hardware not connected, starting software-only session.")

    return True

def end_conversation():
    """End the current screening session and STOP Hardware"""
    # 1. Stop Hardware if running
    if st.session_state.get('hardware_running', False) and st.session_state.get('is_connected', False):
        try:
            client = get_ssh_client()
            # Send Ctrl+C to shell
            if st.session_state.shell:
                st.session_state.shell.send('\x03')
                time.sleep(2)
            
            # Kill processes
            client.exec_command("pkill -f mqtt_to_dynamo.py")
            client.exec_command("pkill -f rpi_emotion_detect.py")
            client.exec_command("pkill -f eye.py")
            
            st.session_state.hardware_running = False
            st.session_state.calibration_step = 0
            print("🛑 Hardware Stopped")
        except Exception as e:
            print(f"Hardware Stop Error: {e}")

    # 2. End DB Session
    if st.session_state.session_id:
        print(f"🛑 Ending session: {st.session_state.session_id}")
        st.session_state.db_handler.end_session(st.session_state.session_id)
        print(f"✅ Session marked as completed")
    
    # 3. Reset Local State
    st.session_state.session_id = None
    st.session_state.agent = None
    st.session_state.messages = []
    st.session_state.conversation_started = False
    st.session_state.last_interaction_time = None
    st.session_state.selected_child_id = None
    st.session_state.selected_child_name = None
    st.session_state.last_db_message_count = 0
    st.session_state.child_window_opened = False
    st.session_state.waiting_for_child_ready = False
    st.session_state.greeting_sent = False

def main():
    # 1. SETUP LAYOUT
    st.set_page_config(layout="wide")
    initialize_session()

    # ===== ADD THIS SECTION HERE (BEFORE loading children) =====
    # Auto-sync messages BEFORE rendering anything
    if st.session_state.conversation_started and st.session_state.monitoring_mode:
        sync_result = sync_messages_from_db()
        if sync_result:
            print("🔄 New messages detected - rerunning...")
            time.sleep(0.3)
            st.rerun()
    # ===== END NEW SECTION =====
    
    if not st.session_state.children_list:
        load_children()
    
    # --- HARDWARE DATA LOOP ---
    # Parse shell output for calibration status
    if st.session_state.get('hardware_running', False) and st.session_state.shell:
        if st.session_state.shell.recv_ready():
            try:
                data = st.session_state.shell.recv(4096).decode("utf-8", errors='ignore')
                
                # PARSE CALIBRATION STEPS
                if "STEP 1" in data: st.session_state.calibration_step = 1
                elif "STEP 2" in data: st.session_state.calibration_step = 2
                elif "STEP 3" in data: st.session_state.calibration_step = 3
                elif "STEP 4" in data: st.session_state.calibration_step = 4
                elif "STEP 5" in data: st.session_state.calibration_step = 5
                elif "SESSION STARTING" in data: st.session_state.calibration_step = 6
                
                # PARSE STATUS (Eyes)
                if "Focused" in data: st.session_state.last_hardware_status = "Focused"
                elif "Distracted" in data: st.session_state.last_hardware_status = "Distracted"
            except:
                pass

    
   # 2. DEFINE COLUMNS (Left: Chat, Right: Controls)
    chat_col, control_col = st.columns([0.8, 0.2], gap="large")

    # ===== ADD THIS DEBUG SECTION =====
    if st.session_state.conversation_started:
        print(f"\n{'='*60}")
        print(f"🎯 CLINICIAN INTERFACE STATUS:")
        print(f"   Session ID: {st.session_state.session_id}")
        print(f"   Conversation started: {st.session_state.conversation_started}")
        print(f"   Monitoring mode: {st.session_state.monitoring_mode}")
        print(f"   Greeting sent: {st.session_state.greeting_sent}")
        print(f"   Local messages: {len(st.session_state.messages)}")
        print(f"{'='*60}\n")
    # ===== END DEBUG SECTION =====

    # ==========================================
    # 🟧 RIGHT COLUMN: CLINICIAN CONTROLS
    # ==========================================
    with control_col:
        st.markdown("##### 👨‍⚕️ Control Settings")

        # Show sync status
        if st.session_state.conversation_started:
            st.caption(f"🔄 Monitoring active")
        # --- NEXUS HARDWARE CONNECT ---
        if not st.session_state.get('is_connected', False):
            if st.button("🔌 Connect Hardware", use_container_width=True):
                with st.spinner("Connecting to Nexus..."):
                    if connect_ssh():
                        st.success("Connected!")
                        time.sleep(1)
                        st.rerun()
        else:
            # HEALTH MONITOR
            with st.expander("🧠 System Health", expanded=False):
                client = get_ssh_client()
                # Emotion AI Status
                emo_run, emo_log = check_process_status(client, "rpi_emotion_detect.py", "/tmp/nexus_emo.log")
                emo_color = "health-running" if emo_run else "health-stopped"
                st.markdown(f"""<div class="health-card {emo_color}"><b>Emotion AI</b><br>{emo_log[-50:]}</div>""", unsafe_allow_html=True)
                
                # MQTT Status
                mqtt_run, mqtt_log = check_process_status(client, "mqtt_to_dynamo.py", "/tmp/nexus_mqtt.log")
                mqtt_color = "health-running" if mqtt_run else "health-stopped"
                st.markdown(f"""<div class="health-card {mqtt_color}"><b>MQTT Bridge</b><br>{mqtt_log[-50:]}</div>""", unsafe_allow_html=True)
                
                if st.button("Disconnect HW"):
                    st.session_state.is_connected = False
                    st.rerun()
        
        st.divider()
        
        if not st.session_state.conversation_started:
            st.subheader("Start Session")
            
            # FIXED: Get clinician_id from session state (set by login system)
            clinician_id = st.session_state.get('user_id')
            
            if not clinician_id:
                st.error("⚠️ User ID not found. Please log in again.")
                st.stop()
            
            if st.session_state.children_list:
                child_options = {
                    f"{child.get('Name', child.get('name', 'Unknown'))}": child.get('ChildID', child.get('child_id'))
                    for child in st.session_state.children_list
                }
                
                selected_display = st.selectbox(
                    "Select Child",  # This label will be hidden if you want
                    options=list(child_options.keys()), 
                    key="child_selector",
                    label_visibility="collapsed"  # Hide default label since we added custom one above
                )
                selected_child_id = child_options[selected_display]
                
                selected_child = next((c for c in st.session_state.children_list if c.get('ChildID', c.get('child_id')) == selected_child_id), None)
                
                if selected_child:
                    # 1. Get Basic Info
                    child_name = selected_child.get('Name', selected_child.get('name', 'N/A'))
                    child_dob_str = selected_child.get('DOB', selected_child.get('date_of_birth', 'N/A'))
                    parent_id = selected_child.get('ParentID', selected_child.get('parent_id'))
                    
                    # 2. Calculate Age Logic
                    child_age = "N/A"
                    if child_dob_str and child_dob_str != 'N/A':
                        try:
                            # Parse the date string (assumes YYYY-MM-DD format)
                            dob_date = datetime.strptime(str(child_dob_str), "%Y-%m-%d")
                            today = datetime.today()
                            
                            # Calculate years
                            age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                            child_age = f"{age} years old"
                        except ValueError:
                            child_age = "Invalid Date"

                    # 3. Get Parent Name from Database
                    # We use the new function we added to db_handler
                    parent_name = "Unknown"
                    if parent_id and "db_handler" in st.session_state:
                        parent_name = st.session_state.db_handler.get_parent_name(parent_id)

                    # 4. Display the simplified info box
                    st.info(f"""
                        **Name:** {child_name}  
                        **Age:** {child_age}  
                        **Parent:** {parent_name}
                    """)
            else:
                st.warning("No children found")
                selected_child_id = None
            
            # FIXED: Pass clinician_id explicitly to start_conversation
            if st.button("▶️ Start Session", type="primary", use_container_width=True, disabled=not selected_child_id):
                if selected_child_id:
                    if start_conversation(selected_child_id, clinician_id):  # ← FIXED: Pass clinician_id here
                        st.success("✅ Session started!")
                        time.sleep(0.5)
                        st.rerun()
        else:
            # Active session controls
            st.success("🟢 Session Active")
            
            # FIXED: Show clinician info in active session
            clinician_name = st.session_state.get('full_name', 'Unknown')
            active_child_id = st.session_state.get('selected_child_id')
            parent_name = "Unknown"
            if active_child_id and st.session_state.children_list:
                # Find the child object in the list
                active_child = next((c for c in st.session_state.children_list if c.get('ChildID', c.get('child_id')) == active_child_id), None)
                
                if active_child:
                    parent_id = active_child.get('ParentID', active_child.get('parent_id'))
                    if parent_id and "db_handler" in st.session_state:
                        parent_name = st.session_state.db_handler.get_parent_name(parent_id)

            st.info(f"**Therapist:** {clinician_name}\n\n**Child:** {st.session_state.selected_child_name}\n\n**Parent:** {parent_name}\n\n**Session:** {st.session_state.session_id}")
            
            # Show Hardware Status
            if st.session_state.get('hardware_running', False):
                status_color = "🟢" if st.session_state.last_hardware_status == "Focused" else "🔴"
                st.markdown(f"**Eye Focus:** {status_color} {st.session_state.last_hardware_status}")

            if st.session_state.waiting_for_child_ready:
                st.warning("⏳ Waiting for child interface...")
            elif st.session_state.greeting_sent:
                st.success("✅ Conversation started!")
            
            # Open child window button (Corrected)
            if not st.session_state.child_window_opened:
                if st.button("🪟 Open Child Window", use_container_width=True, type="primary"):
                    open_child_window()
                    st.session_state.child_window_opened = True
            else:
                st.success("✅ Child window opened")
                # REOPEN BUTTON RESTORED
                if st.button("🔄 Reopen Child Window", use_container_width=True):
                    open_child_window()
            
            st.markdown("---")
            
            if st.button("🛑 End Session", type="secondary", use_container_width=True):
                end_conversation()
                st.success("Session ended!")
                st.rerun()
            
            st.divider()
            st.subheader("📝 Notes")
            note_text = st.text_area("Add observation", key="clinician_note", height=100)
            if st.button("Save Note", use_container_width=True):
                if note_text.strip():
                    st.session_state.db_handler.add_clinician_note(st.session_state.session_id, note_text)
                    st.success("Note saved!")
                    st.rerun()
        
        st.divider()
        with st.expander("⚙️ Robot & Audio"):
            if st.session_state.robot_controller:
                st.session_state.robot_enabled = st.checkbox("Enable Robot Actions", value=st.session_state.robot_enabled)
            st.session_state.enable_tts = st.checkbox("🔊 Voice Output", value=st.session_state.enable_tts)
    
    # ==========================================
    # 🟦 LEFT COLUMN: CHAT INTERFACE
    # ==========================================
    with chat_col:
        st.markdown("<h1>Live Conversation Monitor 💙</h1>", unsafe_allow_html=True)
    
        # --- CALIBRATION WIZARD (Overlay) ---
        # Only show if hardware is running AND calibration is not finished (Step < 6)
        curr_step = st.session_state.get('calibration_step', 0)
        
        if st.session_state.conversation_started and st.session_state.get('hardware_running', False) and 0 < curr_step < 6:
            
            progress = int((curr_step - 1) * 20)
            st.markdown(f"**System Calibration: {progress}% Complete**")
            st.progress(progress)
            
            instr = ["Initializing...", "Look at the CENTER", "Look LEFT Limit", "Look RIGHT Limit", "Look TOP Limit", "Look BOTTOM Limit", "Active"][curr_step]
            
            st.markdown(f"""
            <div class="calib-card">
                <div class="instruction-big">{instr}</div>
                <div class="instruction-small">Instruct the child to hold their gaze steady, then press Capture.</div>
            </div>
            """, unsafe_allow_html=True)
            
            col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
            with col_c2:
                if st.button("✅ Capture Position", use_container_width=True):
                    if st.session_state.shell:
                        st.session_state.shell.send("\n")
                        with st.spinner(f"Calibrating Step {curr_step}..."):
                            time.sleep(1.0)
                        st.rerun()
            
            st.divider() # Separate calibration from chat potential

        # --- MAIN VIEW LOGIC ---
        if not st.session_state.conversation_started:
            st.markdown("""
                <div style='text-align: center; background-color: white; padding: 50px; border-radius: 20px;'>
                    <h2 style='font-size: 2em; color: #2C5F7C;'>Ready to Start</h2>
                    <p style='font-size: 1.3em; color: #555;'>
                        1. <b>Connect Hardware</b> in sidebar (Optional)<br>
                        2. Select a child & Click <b>"Start Session"</b><br>
                        3. Perform Calibration (if hardware connected)<br>
                        4. Open Child Window
                    </p>
                </div>
            """, unsafe_allow_html=True)

        else:
            # Display conversation (ALWAYS show if session started)
            if not st.session_state.messages:
                # Only show waiting message if truly no messages exist
                st.markdown("""
                    <div style='text-align: center; background-color: white; padding: 50px; border-radius: 20px;'>
                        <h2 style='font-size: 2em; color: #667eea;'>⏳ Waiting for conversation to begin...</h2>
                        <p style='font-size: 1.3em; color: #555;'>Messages will appear here once the child starts talking.</p>
                    </div>
                """, unsafe_allow_html=True)
            with st.container(height=650, border=False):
                if not st.session_state.messages:
                    st.markdown("<h3 style='text-align:center;color:#ccc;'>Waiting for conversation...</h3>", unsafe_allow_html=True)
                else:
                    # Display all messages
                    for idx, message in enumerate(st.session_state.messages):
                        avatar = "🤖" if message["role"] == "assistant" else "😊"
                        with st.chat_message(message["role"], avatar=avatar):
                            st.write(message["content"])
                            
                            # ===== ENHANCED ROBOT ACTION DISPLAY =====
                            if message["role"] == "assistant" and message.get("robot_action"):
                                robot_action = message["robot_action"]
                                action_name = robot_action.get('action', 'unknown')
                                reason = robot_action.get('reason', 'No reason provided')
                                
                                # Format action name nicely (jump_forward → Jump Forward)
                                formatted_action = action_name.replace('_', ' ').title()
                            
                                # Display with nice formatting
                                st.info(f"""
                    **🤖 Robot Action:** {formatted_action}  
                    **💭 Reason:** {reason}
                                """.strip())
                            # ===== END ENHANCED DISPLAY =====

                            # Show picture indicator if present
                            if message["role"] == "assistant" and message.get("picture"):
                                picture_info = message['picture']
                                st.success(f"🖼️ Picture shown: {picture_info.get('filename', 'Unknown')} ({picture_info.get('complexity', 'N/A')} complexity)")
        # Auto-refresh
        if st.session_state.conversation_started and st.session_state.monitoring_mode:
            time.sleep(2)
            st.rerun()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"❌ Error occurred")
        with st.expander("Details"):
            st.exception(e)

# ADD cleanup on app shutdown (optional but recommended)
import atexit
atexit.register(AppConfig.stop_child_view)