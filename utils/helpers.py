import bcrypt
import streamlit as st

def hash_password(password):
    # Truncate password to 72 bytes, safely encoding to utf-8
    password_bytes = password.encode('utf-8')[:72]  # max 72 bytes
    safe_password = password_bytes.decode('utf-8', 'ignore')  # ignore incomplete chars
    return bcrypt.hashpw(safe_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    # Truncate password to 72 bytes, safely encoding to utf-8
    password_bytes = password.encode('utf-8')[:72]  # max 72 bytes
    safe_password = password_bytes.decode('utf-8', 'ignore')  # ignore incomplete chars
    return bcrypt.checkpw(safe_password.encode('utf-8'), hashed.encode('utf-8'))

def set_session(user_data):
    st.session_state['logged_in'] = True
    st.session_state['user_role'] = user_data['UserRole']
    st.session_state['user_id'] = user_data['UserID']
