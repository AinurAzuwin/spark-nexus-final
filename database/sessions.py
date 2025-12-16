# CRUD for sessions

from config.aws_config import get_dynamodb
from boto3.dynamodb.conditions import Attr

dynamodb = get_dynamodb()
sessions_table = dynamodb.Table("sessions")

def create_session(session_id, child_id, child_name, session_number, status="ACTIVE"):
    return sessions_table.put_item(
        Item={
            "session_id": session_id,
            "child_id": child_id,
            "child_name": child_name,
            "session_number": session_number,
            "status": status
        }
    )

def get_sessions_by_child(child_id):
    try:
        response = sessions_table.scan(
            FilterExpression=Attr("child_id").eq(child_id)
        )
        return response.get("Items", [])
    except Exception as e:
        print(f"Error accessing sessions table: {e}")
        return []

def get_sessions_by_therapist(therapist_id):
    from database.children import get_children_by_therapist
    children = get_children_by_therapist(therapist_id)
    all_sessions = []
    for child in children:
        sessions = get_sessions_by_child(child['ChildID'])
        all_sessions.extend(sessions)
    return all_sessions

def get_sessions_by_parent(parent_id):
    from database.children import get_children_by_parent
    children = get_children_by_parent(parent_id)
    all_sessions = []
    for child in children:
        child_id = child['ChildID']
        child_name = child['Name']
        sessions = get_sessions_by_child(child_id)
        for session in sessions:
            session['ChildName'] = child_name
            all_sessions.append(session)
    return all_sessions

def get_session_by_id(session_id):
    try:
        response = sessions_table.get_item(Key={"session_id": session_id})
        return response.get("Item")
    except Exception as e:
        print(f"Error accessing sessions table: {e}")
        return None

def update_session_status(session_id, status, end_time=None):
    update_expression = "SET #s = :s"
    expression_attribute_names = {"#s": "status"}
    expression_attribute_values = {":s": status}
    if end_time:
        update_expression += ", EndTime = :et"
        expression_attribute_values[":et"] = end_time
    return sessions_table.update_item(
        Key={"session_id": session_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values
    )

def update_session_feedback(session_id, rating, feedback=None):
    update_expression = "SET rating = :r"
    expression_attribute_values = {":r": rating}
    if feedback:
        update_expression += ", feedback = :f"
        expression_attribute_values[":f"] = feedback
    return sessions_table.update_item(
        Key={"session_id": session_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
    )
