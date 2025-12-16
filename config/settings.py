# Global constants (table names, AWS region)
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env file

# AWS DynamoDB table names
USERS_TABLE = "users"
CHILDREN_TABLE = "children"
SESSIONS_TABLE = "sessions"
MESSAGES_TABLE = "messages"
REPORTS_TABLE = "reports"
APPOINTMENTS_TABLE = "appointments"
FEEDBACK_TABLE = "feedback"

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")