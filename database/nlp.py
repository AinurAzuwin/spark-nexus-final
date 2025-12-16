# CRUD for NLP analysis results

from config.aws_config import get_dynamodb
import json
from typing import Dict, Any

dynamodb = get_dynamodb()
nlp_table = dynamodb.Table("nlp")

def save_nlp_result(session_id: str, nlp_data: Dict[str, Any]):
    """
    Save the full NLP analysis result for a session.
    PK: session_id
    """
    try:
        # Convert dict to JSON string for storage
        nlp_json = json.dumps(nlp_data, ensure_ascii=False)
        return nlp_table.put_item(
            Item={
                "session_id": session_id,
                "nlp_result": nlp_json,
                "timestamp": nlp_data.get("timestamp") or "2023-01-01T00:00:00Z"  # placeholder, adjust as needed
            }
        )
    except Exception as e:
        print(f"Error saving NLP result: {e}")
        raise

def get_nlp_result(session_id: str) -> Dict[str, Any]:
    """
    Retrieve the NLP analysis result for a session.
    """
    try:
        response = nlp_table.get_item(Key={"session_id": session_id})
        item = response.get("Item")
        if item:
            # Parse JSON back to dict
            nlp_data = json.loads(item["nlp_result"])
            return nlp_data
        return {}
    except Exception as e:
        print(f"Error retrieving NLP result: {e}")
        return {}

def update_nlp_result(session_id: str, updated_data: Dict[str, Any]):
    """
    Update the NLP result (e.g., for incremental updates in real-time).
    """
    try:
        current = get_nlp_result(session_id)
        if current:
            current.update(updated_data)
            save_nlp_result(session_id, current)
        else:
            save_nlp_result(session_id, updated_data)
    except Exception as e:
        print(f"Error updating NLP result: {e}")
        raise

def get_previous_nlp_result(session_id: str) -> Dict[str, Any]:
    """
    Retrieve the NLP analysis result for the previous session of the same child.
    """
    from database.sessions import get_session_by_id, get_sessions_by_child
    try:
        current_session = get_session_by_id(session_id)
        if not current_session:
            return {}
        child_id = current_session.get('child_id')
        current_session_number = current_session.get('session_number', 0)
        if current_session_number <= 1:
            return {}  # No previous session
        sessions = get_sessions_by_child(child_id)
        # Sort sessions by session_number
        sessions.sort(key=lambda s: s.get('session_number', 0))
        # Find the previous session
        for session in sessions:
            if session.get('session_number') == current_session_number - 1:
                return get_nlp_result(session['session_id'])
        return {}
    except Exception as e:
        print(f"Error retrieving previous NLP result: {e}")
        return {}
