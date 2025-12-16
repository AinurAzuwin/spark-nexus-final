# CRUD child data

from config.aws_config import get_dynamodb
from boto3.dynamodb.conditions import Attr
from datetime import datetime

dynamodb = get_dynamodb()
children_table = dynamodb.Table("children")

def create_child(child_id, name, dob, parent_id, gender, language_background, diagnosis, ic_number, therapist_id=None, registration_date=None):
    item = {
        "ChildID": child_id,
        "Name": name,
        "DOB": dob,
        "ParentID": parent_id,
        "Gender": gender,
        "LanguageBackground": language_background,
        "Diagnosis": diagnosis,
        "ICNumber": ic_number,
        "TherapistID": therapist_id,
        "RegistrationDate": registration_date or datetime.utcnow().isoformat(),
    }
    return children_table.put_item(Item=item)

def assign_therapist_to_child(child_id, therapist_id, therapist_name):
    return children_table.update_item(
        Key={"ChildID": child_id},
        UpdateExpression="SET TherapistID = :t, TherapistName = :n",
        ExpressionAttributeValues={":t": therapist_id, ":n": therapist_name},
        ReturnValues="UPDATED_NEW"
    )

def get_children_by_parent(parent_id):
    response = children_table.scan(
        FilterExpression=Attr("ParentID").eq(parent_id)
    )
    return response.get("Items", [])

def get_children_by_therapist(therapist_id):
    response = children_table.scan(
        FilterExpression=Attr("TherapistID").eq(therapist_id)
    )
    return response.get("Items", [])

def update_child(child_id, updates):
    """
    Update child fields. updates is a dict of field: value
    """
    update_expression = "SET " + ", ".join(f"{k} = :{k}" for k in updates.keys())
    expression_values = {f":{k}": v for k, v in updates.items()}
    children_table.update_item(
        Key={"ChildID": child_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values
    )
    return True

def get_all_children():
    response = children_table.scan()
    return response.get("Items", [])
