"""
Robust Child-Facing Interface with Audio Completion Tracking
FIXED: Emotion updates immediately when agent response appears
FIXED: Unicode console errors and missing UI elements
"""
import os
import streamlit as st
from audio_handler import AudioHandler
from database_handler import DatabaseHandler
from emotion_display_handler import EmotionDisplayHandler
from llm_agent import LanguageScreeningAgent
from picture_handler import PictureHandler
from robot_controller import RobotController
import agent_settings
import base64
import uuid
import time
import streamlit.components.v1 as components


# Safe print function that handles Unicode errors
def safe_print(message):
    """Print messages safely, handling Unicode encoding errors"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: print ASCII-only version
        ascii_message = message.encode('ascii', 'ignore').decode('ascii')
        print(ascii_message)

# Page config
st.set_page_config(
    page_title="Let's Talk! 😊",
    page_icon="🎈",
    layout="wide",
)

st.markdown("""
    <style>
    /* 1. FIX EMOJI FONTS & GENERAL TYPOGRAPHY */
    html, body, [class*="css"] {
        font-family: 'Nunito', 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif !important;
    }

    /* 2. REMOVE DEFAULT PADDING & SCROLLBARS */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100vw !important;
    }
    
    /* Hide the main page scrollbar */
    section.main {
        overflow: hidden !important; 
    }

    /* 3. HIDE HEADER & FOOTER */
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { display: none !important; }

    /* 4. APP BACKGROUND (MATCHING APP.PY PASTEL BLUE) */
    .stApp {
        background: linear-gradient(180deg, #E8F4F8 0%, #F0F8FF 100%);
        background-attachment: fixed;
    }

    /* 5. FIX FOR TWO-COLUMN LAYOUT - CRITICAL CHANGES */
    /* Target the main horizontal block container */
    div[data-testid="stHorizontalBlock"] {
        display: flex !important;
        align-items: flex-start !important;
        gap: 1rem !important;
    }

    /* Left Column (Emotion) - FIXED POSITION */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:first-child {
        position: sticky !important;
        top: 20px !important;
        height: calc(100vh - 100px) !important;
        overflow: hidden !important;
        flex: 0 0 350px !important;
        max-width: 350px !important;
    }

    /* Right Column (Conversation) - SCROLLABLE */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
        flex: 1 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        max-height: calc(100vh - 100px) !important;
        padding-right: 10px !important;
    }

    /* Custom scrollbar for conversation column */
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child::-webkit-scrollbar {
        width: 8px;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 10px;
    }

    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child::-webkit-scrollbar-thumb:hover {
        background: #5568d3;
    }
    
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {
    scroll-behavior: smooth !important;

    /* EMOTION DISPLAY COLUMN STYLING */
    .emotion-column {
        position: sticky;
        top: 20px;
        height: calc(100vh - 100px);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: white;
        border-radius: 30px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 2px solid #E1E4E8;
    }

    .emotion-title {
        font-size: 2em;
        color: #2C5F7C;
        font-weight: 700;
        margin-bottom: 1rem;
        text-align: center;
    }

    .emotion-display-area {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        min-height: 300px;
    }

    /* 6. CHAT MESSAGE BUBBLES */
    [data-testid="stChatMessage"] {
        background-color: white;
        border-radius: 25px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
        border: 1px solid #E1E4E8;
    }
    
    /* Make the text larger for kids */
    [data-testid="stMarkdownContainer"] p {
        font-size: 1.6rem !important;
        line-height: 1.5;
        color: #2D3748;
    }
    
    /* Make avatars larger */
    [data-testid="stChatMessageAvatar"] {
        width: 60px !important;
        height: 60px !important;
    }

    /* 7. ENHANCED BUTTON STYLING - TARGETS ALL BUTTON CLASSES */
    
    /* Target multiple button selectors to ensure it works */
    div.stButton > button,
    button[data-testid="stBaseButton-secondary"],
    button.st-emotion-cache-1tvz4nm,
    .stButton button,
    [class*="stButton"] button {
        width: 100% !important;
        font-size: 2.2em !important;
        font-weight: 900 !important;
        padding: 1em 2em !important;
        border-radius: 60px !important;
        background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 50%, #4ECDC4 100%) !important;
        color: white !important;
        border: 5px solid white !important;
        box-shadow: 0 10px 30px rgba(255, 107, 107, 0.4),
                    0 0 0 10px rgba(255, 107, 107, 0.1) !important;
        transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) !important;
        text-transform: uppercase !important;
        letter-spacing: 3px !important;
        animation: bounce-gentle 2s ease-in-out infinite !important;
    }
    
    /* Hover effect for all button variations */
    div.stButton > button:hover,
    button[data-testid="stBaseButton-secondary"]:hover,
    button.st-emotion-cache-1tvz4nm:hover,
    .stButton button:hover,
    [class*="stButton"] button:hover {
        transform: scale(1.15) rotate(-2deg) !important;
        box-shadow: 0 15px 40px rgba(255, 107, 107, 0.6),
                    0 0 0 15px rgba(255, 107, 107, 0.2) !important;
        animation: none !important;
    }
    
    /* Active/Click effect */
    div.stButton > button:active,
    button[data-testid="stBaseButton-secondary"]:active,
    button.st-emotion-cache-1tvz4nm:active,
    .stButton button:active,
    [class*="stButton"] button:active {
        transform: scale(0.95) !important;
    }
    
    /* Bounce animation */
    @keyframes bounce-gentle {
        0%, 100% { 
            transform: translateY(0); 
        }
        50% { 
            transform: translateY(-10px); 
        }
    }
    
    /* Override Streamlit's default button text styling */
    div.stButton > button p,
    button[data-testid="stBaseButton-secondary"] p,
    .stButton button p {
        font-size: 1em !important;
        margin: 0 !important;
        color: white !important;
    }

    /* 8. TITLE STYLING (Darker blue for contrast on light bg) */
    h1 {
        color: #2C5F7C !important;
        font-size: 3em !important;
        text-align: center;
        margin-bottom: 1rem !important;
        font-weight: 800 !important;
        text-shadow: none !important;
    }

    /* 9. LISTENING INDICATOR */
    .listening-indicator {
        background: white;
        border: 3px solid #667eea;
        color: #667eea;
        padding: 2rem;
        border-radius: 30px;
        text-align: center;
        font-size: 2em;
        font-weight: bold;
        margin: 30px 0;
        animation: pulse 1.5s infinite;
        box-shadow: 0 10px 20px rgba(102, 126, 234, 0.15);
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    /* 10. WAITING CARD */
    .waiting-card {
        background: white;
        border-radius: 30px;
        padding: 40px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        margin-top: 20px;
        border: 2px solid #E8F4F8;
    }
    
    /* Picture Display Styles */
    .picture-container {
        background: white;
        border-radius: 20px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        text-align: center;
    }
    .picture-frame {
        border: 5px solid #667eea;
        border-radius: 15px;
        overflow: hidden;
        max-width: 600px;
        margin: 0 auto;
    }
    .picture-frame img {
        width: 100%;
        height: auto;
        display: block;
    }
    .picture-prompt {
        font-size: 1.8em;
        color: #667eea;
        font-weight: bold;
        margin-top: 15px;
    }

    /* Conversation Column Styling */
    .conversation-column {
        background: white;
        border-radius: 30px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border: 2px solid #E1E4E8;
        min-height: calc(100vh - 100px);
    }
    </style>
""", unsafe_allow_html=True)

def initialize_session():
    """Initialize session state"""
    if "audio_handler" not in st.session_state:
        st.session_state.audio_handler = AudioHandler()
        # Pre-load common phrases for instant TTS
        if agent_settings.ENABLE_TTS_CACHE:
            st.session_state.audio_handler.preload_common_phrases()
    if "db_handler" not in st.session_state:
        st.session_state.db_handler = DatabaseHandler()
    if "robot_controller" not in st.session_state:
        if agent_settings.ENABLE_ROBOT_ACTIONS:
            st.session_state.robot_controller = RobotController()
            print("🤖 Robot controller initialized in child interface")
        else:
            st.session_state.robot_controller = None
    if "emotion_handler" not in st.session_state:
        try:
            st.session_state.emotion_handler = EmotionDisplayHandler()
        except Exception as e:
            safe_print(f"[WARNING] Could not initialize emotion handler: {e}")
            st.session_state.emotion_handler = None
    if "picture_handler" not in st.session_state:
        st.session_state.picture_handler = PictureHandler()
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = None
    if "last_message_count" not in st.session_state:
        st.session_state.last_message_count = 0
    if "audio_played_count" not in st.session_state:
        st.session_state.audio_played_count = 0
    if "last_audio_bytes" not in st.session_state:
        st.session_state.last_audio_bytes = None
    if "waiting_for_response" not in st.session_state:
        st.session_state.waiting_for_response = False
    if "current_emotion" not in st.session_state:
        st.session_state.current_emotion = "neutral"
    if "audio_start_time" not in st.session_state:
        st.session_state.audio_start_time = None
    if "audio_duration" not in st.session_state:
        st.session_state.audio_duration = 0
    if "processed_audio_hash" not in st.session_state:
        st.session_state.processed_audio_hash = None
    if "agent" not in st.session_state:
        st.session_state.agent = None
      
def estimate_audio_duration(text: str) -> float:
    """
    Estimate audio duration based on text length
    Approximate speaking rate: ~150 words per minute at normal speed
    With TTS_SPEED = 0.90, adjust accordingly
    """
    words = len(text.split())
    # Base: 150 words/min = 2.5 words/sec
    # With speed 0.90: 2.5 * 0.90 = 2.25 words/sec
    speaking_rate = 2.25  # words per second at speed 0.90
    duration = words / speaking_rate
    # Add 1 second buffer for loading/processing
    return duration + 1.0

def create_audio_player_with_callback(audio_bytes, duration_estimate):
    """
    Create auto-playing audio element with completion callback
    Signals to database when audio finishes
    """
    try:
        b64 = base64.b64encode(audio_bytes).decode()
        el_id = f"audio_{uuid.uuid4().hex[:8]}"
        
        # Convert duration to milliseconds
        duration_ms = int(duration_estimate * 1000)
        
        return f"""
<audio id="{el_id}" autoplay style="display:none;">
    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
</audio>
<script>
    var audio = document.getElementById('{el_id}');
    
    // Play audio
    audio.play().catch(function(error) {{
        console.log("Audio play failed: " + error);
    }});
    
    // Set timeout to mark completion (fallback if ended event doesn't fire)
    setTimeout(function() {{
        console.log("Audio playback completed (timeout)");
    }}, {duration_ms});
    
    // Also listen for ended event
    audio.addEventListener('ended', function() {{
        console.log("Audio playback completed (ended event)");
    }});
</script>
"""
    except:
        return None

def display_emotion_in_column(emotion: str):
    """Display robot emotion GIF in the left column"""
    if not st.session_state.emotion_handler:
        # Fallback: show large emoji if handler is not available
        st.markdown(f"""
            <div style='text-align: center; padding: 2rem;'>
            </div>
        """, unsafe_allow_html=True)
        return
    
    try:
        emotion_html = st.session_state.emotion_handler.create_emotion_html(
            emotion, 
            width=300, 
            height=300
        )
        if emotion_html:
            st.markdown(emotion_html, unsafe_allow_html=True)
        else:
            # Fallback if no HTML returned
            st.markdown(f"""
                <div style='text-align: center; padding: 2rem;'>
                </div>
            """, unsafe_allow_html=True)
        
    except Exception as e:
        safe_print(f"[ERROR] Error displaying emotion: {e}")
        # Show fallback emoji
        st.markdown(f"""
            <div style='text-align: center; padding: 2rem;'>
                <div style='font-size: 8em;'>🤖</div>
            </div>
        """, unsafe_allow_html=True)

def display_picture(picture_path: str):
    """
    Display a picture for the child to describe
    
    Args:
        picture_path: Path to the picture file
    """
    try:
        # CRITICAL: Check if path is absolute or relative
        if not os.path.isabs(picture_path):
            # Make it absolute relative to current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            picture_path = os.path.join(current_dir, picture_path)
        
        safe_print(f"[INFO] Attempting to load picture from: {picture_path}")
        
        # Check if file exists
        if not os.path.exists(picture_path):
            safe_print(f"[ERROR] Picture file not found: {picture_path}")
            
            # Try alternative paths
            alternatives = [
                os.path.join(os.path.dirname(__file__), "picture_prompts", os.path.basename(picture_path)),
                os.path.join("picture_prompts", os.path.basename(picture_path)),
                picture_path
            ]
            
            for alt_path in alternatives:
                safe_print(f"[INFO] Trying alternative: {alt_path}")
                if os.path.exists(alt_path):
                    picture_path = alt_path
                    safe_print(f"[SUCCESS] Found at: {alt_path}")
                    break
            else:
                # Still not found - show placeholder
                safe_print(f"[ERROR] Could not find picture in any location")
                st.markdown(f"""
                    <div class="picture-container">
                        <div style='background: #f0f0f0; padding: 100px; text-align: center; border-radius: 15px;'>
                            <div style='font-size: 4em;'>🖼️</div>
                            <div style='font-size: 1.5em; color: #666; margin-top: 20px;'>
                                Picture: {os.path.basename(picture_path)}
                            </div>
                            <div style='font-size: 1em; color: #999; margin-top: 10px;'>
                                (File not found)
                            </div>
                        </div>
                        <div class="picture-prompt">👀 What do you see in this picture?</div>
                    </div>
                """, unsafe_allow_html=True)
                return
        
        # Get base64 encoding
        with open(picture_path, 'rb') as f:
            image_bytes = f.read()
            picture_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        if picture_base64:
            # Detect image format
            file_ext = os.path.splitext(picture_path)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(file_ext, 'image/jpeg')
            
            # Display picture with nice frame
            st.markdown(f"""
                <div class="picture-container">
                    <div class="picture-frame">
                        <img src="data:{mime_type};base64,{picture_base64}" alt="Picture to describe">
                    </div>
                    <div class="picture-prompt">👀 What do you see in this picture?</div>
                </div>
            """, unsafe_allow_html=True)
            
            safe_print(f"[SUCCESS] Displayed picture: {picture_path}")
        else:
            safe_print(f"[ERROR] Could not encode picture to base64")
            
    except Exception as e:
        safe_print(f"[ERROR] Error displaying picture: {e}")
        import traceback
        traceback.print_exc()
        
        # Show error placeholder
        st.markdown(f"""
            <div class="picture-container">
                <div style='background: #ffe6e6; padding: 50px; text-align: center; border-radius: 15px; border: 2px dashed #ff0000;'>
                    <div style='font-size: 3em;'>⚠️</div>
                    <div style='font-size: 1.2em; color: #cc0000; margin-top: 10px;'>
                        Could not load picture
                    </div>
                    <div style='font-size: 0.9em; color: #666; margin-top: 5px;'>
                        {str(e)}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def get_active_session_data():
    """Get the full active session object from DB"""
    try:
        sessions = st.session_state.db_handler.get_all_sessions(limit=5000)
        sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        for session in sessions:
            if session.get('status') == 'active':
                return session
        return None
    except Exception as e:
        safe_print(f"[ERROR] Error checking sessions: {e}")
        return None

def signal_child_ready(session_id):
    """Signal to the database that child interface is ready"""
    try:
        success = st.session_state.db_handler.update_session_metadata(
            session_id,
            {'child_ready': True}
        )
        return success
    except Exception as e:
        safe_print(f"[ERROR] Error sending ready signal: {e}")
        return False

def load_messages(session_id):
    if not session_id:
        return []
    return st.session_state.db_handler.get_session_messages(session_id)

def send_response(text, session_id):
    if not session_id or not text.strip():
        return False
    return st.session_state.db_handler.add_message(session_id, "user", text)

def is_audio_currently_playing():
    """Check if audio is still playing based on start time and duration"""
    if st.session_state.audio_start_time is None:
        return False
    
    elapsed = time.time() - st.session_state.audio_start_time
    return elapsed < st.session_state.audio_duration

def update_emotion_for_latest_message(messages):
    """
    FIXED: Update emotion immediately when new assistant message arrives
    This function runs BEFORE displaying messages to ensure emotion changes instantly
    """
    if not messages:
        return
    
    # Get the most recent assistant message
    latest_assistant_msg = None
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            latest_assistant_msg = msg
            break
    
    if not latest_assistant_msg:
        return
    
    # Extract metadata
    msg_metadata = latest_assistant_msg.get('metadata', {})
    
    # Build context dictionary
    context = {
        'detected_emotion': msg_metadata.get('detected_emotion', 'neutral'),
        'robot_action': msg_metadata.get('robot_action', {}),
        'previous_emotion': st.session_state.current_emotion
    }
    
    # Use emotion handler to select emotion
    if st.session_state.emotion_handler:
        selected_emotion = st.session_state.emotion_handler.select_emotion(
            latest_assistant_msg["content"],
            context=context
        )
    else:
        # Fallback: use stored emotion or default
        selected_emotion = msg_metadata.get('emotion', 'neutral')
    
    # Update current emotion IMMEDIATELY
    if selected_emotion != st.session_state.current_emotion:
        safe_print(f"[EMOTION] Change: {st.session_state.current_emotion} -> {selected_emotion}")
        st.session_state.current_emotion = selected_emotion

def main():
    initialize_session()
    
    # Get the current active session
    session_data = get_active_session_data()
    
    # NO ACTIVE SESSION - Show centered waiting screen
    if not session_data:
        if st.session_state.active_session_id is not None:
            st.session_state.active_session_id = None
            st.session_state.last_message_count = 0
            st.session_state.audio_played_count = 0
            st.session_state.current_emotion = "neutral"
            st.session_state.audio_start_time = None
            st.session_state.audio_duration = 0
            st.session_state.processed_audio_hash = None
        
        st.markdown("<h1>Let's Talk Together! 🎈</h1>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            display_emotion_in_column("neutral")
            
            st.markdown("""
                <div style='text-align: center; padding: 3rem;'>
                    <div style='font-size: 3em; margin-bottom: 1rem;'>🎮</div>
                    <div style='font-size: 2em; color: #667eea;'>Waiting for game to start...</div>
                    <div style='font-size: 1.2em; color: #888; margin-top: 1rem;'>
                        (Clinician needs to click 'Start Session')
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        time.sleep(3)
        st.rerun()
        return

    # Update local session ID
    current_session_id = session_data.get('session_id')
    
    if current_session_id != st.session_state.active_session_id:
        st.session_state.active_session_id = current_session_id
        st.session_state.last_message_count = 0
        st.session_state.audio_played_count = 0
        st.session_state.waiting_for_response = False
        st.session_state.current_emotion = "neutral"
        st.session_state.audio_start_time = None
        st.session_state.audio_duration = 0
        st.session_state.processed_audio_hash = None
    
    # Check if ready
    metadata = session_data.get('metadata', {})
    is_ready_in_db = metadata.get('child_ready', False)

    # WAITING FOR START - Show button to start
    if not is_ready_in_db:
        st.markdown("<h1>Let's Talk Together! 🎈</h1>", unsafe_allow_html=True)
        
        # Display emotion GIF
        display_emotion_in_column("surprise")
        
        # Welcome message and button
        st.markdown("""
            <div style='text-align: center; padding: 0.5rem; margin-top: 1rem;'>
                <div style='font-size: 5em; margin-bottom: 1rem;'>👋</div>
                <div style='font-size: 2.5em; color: #667eea; margin-bottom: 2rem; font-weight: bold;'>
                    Hi there! Are you ready to play?
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Centered button with spacing
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 CLICK TO START", use_container_width=True, key="start_button"):
                with st.spinner("Getting ready..."):
                    # Initialize agent for this session
                    st.session_state.agent = LanguageScreeningAgent()
                    st.session_state.agent.set_session_id(current_session_id)
                    
                    # Generate greeting immediately
                    result = st.session_state.agent.start_conversation()
                    greeting = result['response']
                    robot_action = result.get('robot_action')
                    
                    # ===== DEBUG SECTION =====
                    print(f"\n{'='*60}")
                    print(f"🔍 ROBOT EXECUTION CHECK:")
                    print(f"   result keys: {result.keys()}")
                    print(f"   robot_action value: {result.get('robot_action')}")
                    print(f"   robot_action type: {type(result.get('robot_action'))}")
                    print(f"   robot_controller exists: {st.session_state.robot_controller is not None}")
                    if robot_action:
                        print(f"   action_name: {robot_action.get('action')}")
                        print(f"   reason: {robot_action.get('reason')}")
                    else:
                        print(f"   ❌ robot_action is None or empty!")
                    print(f"{'='*60}\n")
                    # ===== END DEBUG =====

                    # Execute robot action immediately
                    robot_action = result.get('robot_action')
                    if robot_action and st.session_state.robot_controller:
                        action_name = robot_action.get('action')
                        reason = robot_action.get('reason', '')
                        print(f"🤖 Executing robot action: {action_name} ({reason})")
                        success = st.session_state.robot_controller.perform_action(action_name)
                        print(f"   Execution result: {success}")
                    # Execute robot action immediately
                    if robot_action and st.session_state.robot_controller:
                        action_name = robot_action.get('action')
                        print(f"🤖 Executing greeting robot action: {action_name}")
                        st.session_state.robot_controller.perform_action(action_name)
                    # ===== END NEW SECTION =====
                    
                    # Prepare message data with TTS
                    message_data = {
                        "role": "assistant",
                        "content": greeting,
                        "robot_action": robot_action,
                        "emotion": result.get('emotion')
                    }
                    
                    # Generate TTS
                    if agent_settings.ENABLE_TEXT_TO_SPEECH:
                        audio_bytes = st.session_state.audio_handler.text_to_speech(greeting)
                        if audio_bytes:
                            message_data["audio"] = audio_bytes
                    
                    # Save to database
                    metadata = {}
                    if result.get('emotion'):
                        metadata['emotion'] = result.get('emotion')
                    if result.get('robot_action'):  # ← ADD THIS
                        metadata['robot_action'] = result.get('robot_action')  # ← ADD THIS

                    success = st.session_state.db_handler.add_message(
                        current_session_id,
                        "assistant",
                        greeting,
                        metadata=metadata if metadata else None
                    )
                    
                    if success:
                        # Signal child is ready
                        st.session_state.db_handler.update_session_metadata(
                            current_session_id,
                            {'child_ready': True}
                        )
                        st.success("✅ Ready to talk!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Connection failed. Please try again.")
        
        return

    # CONVERSATION ACTIVE - TWO COLUMN LAYOUT
    st.markdown("<h1>Let's Talk Together! 🎈</h1>", unsafe_allow_html=True)
    
    # Load messages FIRST
    messages = load_messages(st.session_state.active_session_id)
    
    # CRITICAL FIX: Update emotion BEFORE rendering anything
    update_emotion_for_latest_message(messages)
    
    # Create two columns: emotion on left, conversation on right
    emotion_col, conversation_col = st.columns([1, 2])
    
    # LEFT COLUMN - EMOTION DISPLAY + AUDIO INPUT
    with emotion_col:
        st.markdown("""
            <div style='text-align: center; padding: 2rem 0;'></div>
        """, unsafe_allow_html=True)
        
        # Display current emotion (already updated above)
        display_emotion_in_column(st.session_state.current_emotion)
        
        st.markdown("---")
        
        # AUDIO INPUT AREA - Always visible here!
        if is_audio_currently_playing():
            remaining = st.session_state.audio_duration - (time.time() - st.session_state.audio_start_time)
            if remaining > 0:
                st.markdown(f"""
                    <div style='text-align: center; padding: 1.5rem;'>
                        <div style='font-size: 1.5em; color: #667eea;'>🔊 Speaking...</div>
                        <div style='font-size: 1em; color: #888;'>({remaining:.0f}s)</div>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
        elif messages and messages[-1]['role'] == 'assistant' and not st.session_state.waiting_for_response:
            if agent_settings.ENABLE_SPEECH_TO_TEXT:
                st.markdown("""
                    <div style='text-align: center; margin-bottom: 0.5rem;'>
                        <div style='font-size: 1.3em; color: #667eea; font-weight: bold;'>🎤 Your Turn!</div>
                    </div>
                """, unsafe_allow_html=True)
                
                audio_file = st.audio_input("Click to record")
                
                if audio_file is not None:
                    audio_bytes = audio_file.getvalue()
                    
                    import hashlib
                    audio_hash = hashlib.md5(audio_bytes).hexdigest()
                    
                    if audio_hash != st.session_state.processed_audio_hash:
                        st.session_state.processed_audio_hash = audio_hash
                        
                        with st.spinner("🎧 Listening..."):
                            transcribed = st.session_state.audio_handler.transcribe_audio(audio_bytes)
                            
                            if transcribed and transcribed.strip():
                                if send_response(transcribed, st.session_state.active_session_id):
                                    st.session_state.waiting_for_response = True
                                    st.success(f"✅ Got it!")
                                    
                                    with st.spinner("🤔 Thinking..."):
                                        if not st.session_state.agent:
                                            st.session_state.agent = LanguageScreeningAgent()
                                            st.session_state.agent.set_session_id(st.session_state.active_session_id)
                                        
                                        result = st.session_state.agent.chat(transcribed)
                                        
                                        robot_action = result.get('robot_action')
                                        if robot_action and st.session_state.robot_controller:
                                            action_name = robot_action.get('action')
                                            reason = robot_action.get('reason', '')
                                            print(f"🤖 Executing robot action: {action_name} ({reason})")
                                            st.session_state.robot_controller.perform_action(action_name)
                                        
                                        tts_future = None
                                        if agent_settings.ENABLE_TEXT_TO_SPEECH:
                                            tts_future = st.session_state.audio_handler.text_to_speech_parallel(result['response'])
                                        
                                        metadata = {}
                                        if result.get('emotion'):
                                            metadata['emotion'] = result['emotion']
                                        if result.get('robot_action'):
                                            metadata['robot_action'] = result['robot_action']
                                        if result.get('picture'):
                                            picture_info = result['picture']
                                            metadata['picture_path'] = picture_info['filepath']
                                            metadata['picture_filename'] = picture_info['filename']
                                            metadata['picture_complexity'] = picture_info['complexity']
                                        
                                        st.session_state.db_handler.add_message(
                                            st.session_state.active_session_id,
                                            "assistant",
                                            result['response'],
                                            metadata=metadata if metadata else None
                                        )
                                        
                                        st.session_state.waiting_for_response = False
                                        time.sleep(0.5)
                                        st.rerun()
                            else:
                                st.error("Try again!")
        
        elif st.session_state.waiting_for_response:
            st.markdown("""
                <div style='text-align: center; padding: 1.5rem;'>
                    <div style='font-size: 1.5em; color: #667eea;'>🤔 Thinking...</div>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(2)
            st.rerun()
        
        else:
            time.sleep(1)
            st.rerun()
    
    # RIGHT COLUMN - CONVERSATION ONLY
    with conversation_col:
        # Waiting for first greeting
        with st.container(height=750, border=False):
            if not messages:
                st.markdown("""
                    <div style='text-align: center; padding: 3rem;'>
                        <div style='font-size: 2.5em; color: #667eea;'>🤖 Getting Ready...</div>
                        <div style='font-size: 1.3em; color: #666;'>The robot is waking up!</div>
                    </div>
                """, unsafe_allow_html=True)
                time.sleep(2)
                st.rerun()
                return
            
            # Track audio playback
            newly_started_audio = False
            
            # Display messages
            for idx, message in enumerate(messages):
                avatar = "🤖" if message["role"] == "assistant" else "😊"
                
                with st.chat_message(message["role"], avatar=avatar):
                    st.write(message["content"])
                    
                    # Check if this message has a picture
                    if message["role"] == "assistant":
                        msg_metadata = message.get('metadata', {})
                        picture_path = msg_metadata.get('picture_path')
                        
                        if picture_path:
                            display_picture(picture_path)
                    
                    # Auto-play TTS for new assistant messages
                    if (message["role"] == "assistant" and 
                        idx >= st.session_state.audio_played_count and
                        agent_settings.ENABLE_TEXT_TO_SPEECH):
                        
                        safe_print(f"[AUDIO] Generating audio for message {idx}")
                        audio_bytes = st.session_state.audio_handler.text_to_speech(message["content"])
                        
                        if audio_bytes:
                            duration = estimate_audio_duration(message["content"])
                            safe_print(f"[AUDIO] Estimated duration: {duration:.1f} seconds")
                            
                            audio_html = create_audio_player_with_callback(audio_bytes, duration)
                            if audio_html:
                                components.html(audio_html, height=0)
                                
                                st.session_state.audio_played_count = idx + 1
                                st.session_state.audio_start_time = time.time()
                                st.session_state.audio_duration = duration
                                newly_started_audio = True
                                
                                safe_print(f"[AUDIO] Started at {st.session_state.audio_start_time}")
            
            # Check for new messages
            if len(messages) > st.session_state.last_message_count:
                st.session_state.last_message_count = len(messages)
                st.session_state.waiting_for_response = False
                
                if newly_started_audio:
                    safe_print(f"[AUDIO] Waiting {st.session_state.audio_duration:.1f}s for completion...")
                    time.sleep(st.session_state.audio_duration + 0.5)
                else:
                    time.sleep(0.5)
                st.rerun()
        


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("😕 Oops! Something went wrong.")
        with st.expander("Details"):
            st.exception(e)