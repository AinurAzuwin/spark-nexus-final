# CRUD for messages

from config.aws_config import get_dynamodb
from boto3.dynamodb.conditions import Attr

dynamodb = get_dynamodb()
messages_table = dynamodb.Table("messages")

def create_message(message_id, session_id, sender, text, timestamp):
    return messages_table.put_item(
        Item={
            "MessageID": message_id,
            "SessionID": session_id,
            "Sender": sender,  # e.g., "patient" or "ai_agent"
            "Text": text,
            "Timestamp": timestamp
        }
    )

def get_messages_by_session(session_id):
    try:
        response = messages_table.scan(
            FilterExpression=Attr("session_id").eq(session_id)
        )
        # Sort by timestamp
        items = response.get("Items", [])
        items.sort(key=lambda x: x['timestamp'])
        # Map to expected format: Sender from role, Text from content, Timestamp from timestamp
        for msg in items:
            msg['Sender'] = msg.pop('role')
            msg['Text'] = msg.pop('content')
            msg['Timestamp'] = msg.pop('timestamp')
        return items
    except Exception as e:
        print(f"Error accessing messages table: {e}")
        return []

def get_messages_by_child(child_id):
    # This might require joining with sessions, but for simplicity, assuming we can get session_ids first
    # For now, return empty or implement later if needed
    return []

def get_recent_messages_by_therapist(therapist_id, limit=10):
    from database.sessions import get_sessions_by_therapist
    sessions = get_sessions_by_therapist(therapist_id)
    all_messages = []
    for session in sessions:
        messages = get_messages_by_session(session['session_id'])
        all_messages.extend(messages)
    # Sort by timestamp descending and limit
    all_messages.sort(key=lambda x: x['Timestamp'], reverse=True)
    return all_messages[:limit]
