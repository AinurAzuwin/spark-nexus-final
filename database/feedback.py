# CRUD session feedback

from config.aws_config import get_dynamodb
from boto3.dynamodb.conditions import Attr

dynamodb = get_dynamodb()
feedback_table = dynamodb.Table("feedback")

def create_feedback(feedback_id, child_id, parent_id, therapist_id, rating, notes):
    return feedback_table.put_item(
        Item={
            "FeedbackID": feedback_id,
            "ChildID": child_id,
            "ParentID": parent_id,
            "TherapistID": therapist_id,
            "Rating": rating,
            "Notes": notes
        }
    )

def get_feedback_by_child(child_id):
    response = feedback_table.scan(
        FilterExpression=Attr("ChildID").eq(child_id)
    )
    return response.get("Items", [])

def submit_feedback():
    pass
