"""
Configuration for Language Screening Agent
UPDATED: Optimized for faster audio processing
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- CRITICAL FIX START ---
# Get the absolute path of the folder where THIS file (agent_settings.py) lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Join that path with your filename
SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, "system-prompt.txt")

# API Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Fast model

# Agent Settings
SYSTEM_PROMPT_PATH = "system-prompt.txt"
TEMPERATURE = 0.7
RESPONSE_TIMEOUT_SECONDS = 30

# Audio Settings
ENABLE_SPEECH_TO_TEXT = True
ENABLE_TEXT_TO_SPEECH = True

# OPTIMIZED AUDIO SETTINGS
TTS_VOICE = "nova"  # Child-friendly voice (alternatives: "alloy", "echo", "shimmer")
TTS_SPEED = 0.95    # Slightly slower for clarity (0.90-1.0 recommended for children)
                    # This affects playback speed, NOT generation speed

# AWS DynamoDB Settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# DynamoDB Table Names
DYNAMODB_SESSIONS_TABLE_NAME = os.getenv("DYNAMODB_SESSIONS_TABLE_NAME", "sessions")
DYNAMODB_CHILDREN_TABLE_NAME = os.getenv("DYNAMODB_CHILDREN_TABLE_NAME", "children")
DYNAMODB_MESSAGES_TABLE_NAME = os.getenv("DYNAMODB_MESSAGES_TABLE_NAME", "messages")
DYNAMODB_EMOTION_TABLE_NAME = os.getenv("DYNAMODB_EMOTION_TABLE_NAME", "Emotion")

# Robot Settings (WaveGo)
ENABLE_ROBOT_ACTIONS = os.getenv("ENABLE_ROBOT_ACTIONS", "True").lower() == "true"
ROBOT_IP = os.getenv("ROBOT_IP")  
ROBOT_PORT = int(os.getenv("ROBOT_PORT"))

# PERFORMANCE TUNING
USE_LOCAL_WHISPER = False  # Set to True to use local Whisper (faster if you have good CPU/GPU)
WHISPER_MODEL = "tiny"     # Options: tiny (fastest), base, small, medium, large
                           # "tiny" is ~10x faster than "base" with minimal accuracy loss

# TTS Caching (for repeated phrases)
ENABLE_TTS_CACHE = True
TTS_CACHE_SIZE = 50  # Number of phrases to cache

# Common phrases to pre-cache (optional - speeds up first use)
COMMON_TTS_PHRASES = [
    "Great job!",
    "That's correct!",
    "Good try!",
    "Can you tell me more?",
    "What do you think?",
    "Excellent!",
    "Nice work!",
]