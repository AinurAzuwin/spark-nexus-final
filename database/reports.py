# CRUD auto reports

from config.aws_config import get_dynamodb
from boto3.dynamodb.conditions import Attr

dynamodb = get_dynamodb()
reports_table = dynamodb.Table("reports")

def create_report(report_id, child_id, therapist_id, session_id, nlp_text, approved=False, date=None):
    from datetime import datetime
    if date is None:
        date = datetime.now().isoformat()
    return reports_table.put_item(
        Item={
            "ReportID": report_id,
            "ChildID": child_id,
            "TherapistID": therapist_id,
            "SessionID": session_id,
            "NLP_Text": nlp_text,  # Auto-generated text from LLM/NLP
            "Approved": approved,
            "Date": date
        }
    )

def approve_report(report_id):
    return reports_table.update_item(
        Key={"ReportID": report_id},
        UpdateExpression="SET Approved = :val",
        ExpressionAttributeValues={":val": True},
        ReturnValues="UPDATED_NEW"
    )

def get_reports_by_child(child_id):
    response = reports_table.scan(
        FilterExpression=Attr("ChildID").eq(child_id)
    )
    return response.get("Items", [])

def get_reports_by_therapist(therapist_id):
    response = reports_table.scan(
        FilterExpression=Attr("TherapistID").eq(therapist_id)
    )
    return response.get("Items", [])

def update_report_approval(report_id, approved):
    return reports_table.update_item(
        Key={"ReportID": report_id},
        UpdateExpression="SET Approved = :val",
        ExpressionAttributeValues={":val": approved},
        ReturnValues="UPDATED_NEW"
    )

def update_report_notes(report_id, notes):
    return reports_table.update_item(
        Key={"ReportID": report_id},
        UpdateExpression="SET Notes = :val",
        ExpressionAttributeValues={":val": notes},
        ReturnValues="UPDATED_NEW"
    )

def update_report_text(report_id, nlp_text):
    return reports_table.update_item(
        Key={"ReportID": report_id},
        UpdateExpression="SET NLP_Text = :val",
        ExpressionAttributeValues={":val": nlp_text},
        ReturnValues="UPDATED_NEW"
    )

def get_all_reports():
    response = reports_table.scan()
    return response.get("Items", [])
