# CRUD bookings

from config.aws_config import get_dynamodb
from boto3.dynamodb.conditions import Attr
from datetime import datetime, timedelta

dynamodb = get_dynamodb()
appointments_table = dynamodb.Table("appointments")

def create_appointment(appointment_id, child_id, therapist_id, date_time, status="PENDING", parent_id=None, rejection_note=None):
    item = {
        "AppointmentID": appointment_id,
        "ChildID": child_id,
        "TherapistID": therapist_id,
        "DateTime": date_time,
        "Status": status
    }
    if parent_id:
        item["ParentID"] = parent_id
    if rejection_note:
        item["RejectionNote"] = rejection_note
    return appointments_table.put_item(Item=item)

def update_appointment_status(appointment_id, status, rejection_note=None):
    update_expression = "SET #status = :val"
    expression_attribute_names = {"#status": "Status"}
    expression_attribute_values = {":val": status}
    if rejection_note:
        update_expression += ", #note = :note"
        expression_attribute_names["#note"] = "RejectionNote"
        expression_attribute_values[":note"] = rejection_note
    return appointments_table.update_item(
        Key={"AppointmentID": appointment_id},
        UpdateExpression=update_expression,
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
        ReturnValues="UPDATED_NEW"
    )

def get_appointments_by_parent(parent_id):
    response = appointments_table.scan(
        FilterExpression=Attr("ParentID").eq(parent_id)
    )
    return response.get("Items", [])

def get_appointments_by_therapist(therapist_id):
    response = appointments_table.scan(
        FilterExpression=Attr("TherapistID").eq(therapist_id)
    )
    return response.get("Items", [])

def get_available_slots(therapist_id):
    # Get existing appointments for the therapist
    existing_appointments = get_appointments_by_therapist(therapist_id)
    # Collect booked slots (pending or approved)
    booked_slots = {appt['DateTime'] for appt in existing_appointments if appt['Status'] in ['PENDING', 'APPROVED']}

    # Generate possible slots for the next 14 days, weekdays 9am-5pm
    slots = []
    now = datetime.now()
    for days in range(1, 15):
        date = now + timedelta(days=days)
        if date.weekday() < 5:  # Monday to Friday
            for hour in range(9, 17):  # 9:00 to 16:00
                slot = date.strftime("%Y-%m-%d") + f" {hour:02d}:00"
                if slot not in booked_slots:
                    slots.append(slot)
    return slots

def get_upcoming_approved_appointments_by_parent(parent_id):
    response = appointments_table.scan(
        FilterExpression=Attr("ParentID").eq(parent_id) & Attr("Status").eq("APPROVED")
    )
    items = response.get("Items", [])
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    upcoming = []
    for item in items:
        appt_date_str = item['DateTime'].split(' ')[0]  # Get date part YYYY-MM-DD
        if appt_date_str >= today_str:
            upcoming.append(item)
    return upcoming

def get_upcoming_approved_appointments_by_therapist(therapist_id):
    response = appointments_table.scan(
        FilterExpression=Attr("TherapistID").eq(therapist_id) & Attr("Status").eq("APPROVED")
    )
    items = response.get("Items", [])
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    upcoming = []
    for item in items:
        appt_date_str = item['DateTime'].split(' ')[0]  # Get date part YYYY-MM-DD
        if appt_date_str >= today_str:
            upcoming.append(item)
    return upcoming
