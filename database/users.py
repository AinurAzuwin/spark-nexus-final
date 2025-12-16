import boto3
import uuid
from utils.helpers import hash_password, verify_password, set_session
from config.aws_config import get_dynamodb
from config.settings import USERS_TABLE
from datetime import datetime

dynamodb = get_dynamodb()
users_table = dynamodb.Table(USERS_TABLE)

def create_user(email, password, role, full_name, contact_number, license_id=None, registration_date=None):
    existing_user = get_user_by_email(email)
    if existing_user:
        return {"success": False, "message": "User already exists"}

    user_id = str(uuid.uuid4())
    hashed_password = hash_password(password)


    item = {
    'UserID': user_id,
    'Email': email,
    'Password': hashed_password,
    'UserRole': role,
    'FullName': full_name,
    'ContactNumber': contact_number,
    'Approved': False if role == "THERAPIST" else True,
    'RegistrationDate': registration_date if registration_date else datetime.utcnow().isoformat() 
    }

    if role == "THERAPIST" and license_id:
        item['LicenseID'] = license_id

    users_table.put_item(Item=item)
    return {"success": True, "message": "User created"}


def get_user_by_email(email):
    response = users_table.scan(
        FilterExpression="Email = :email_val",
        ExpressionAttributeValues={":email_val": email}
    )
    items = response.get('Items', [])
    if items:
        return items[0]
    return None

def authenticate_user(email, password):
    user = get_user_by_email(email)
    if user and verify_password(password, user['Password']):
        return user  # return the user object for session management
    return None

def get_all_users():
    response = users_table.scan()
    return response.get('Items', [])

def update_user_approval(email, approved):
    user = get_user_by_email(email)
    if not user:
        return False
    users_table.update_item(
        Key={'UserID': user['UserID']},
        UpdateExpression="SET Approved = :val",
        ExpressionAttributeValues={':val': approved}
    )
    return True

def register_new_user(email, password, role, full_name, contact_number, license_id=None, registration_date=None):
    result = create_user(email, password, role, full_name, contact_number, license_id, registration_date)
    if result["success"]:
        return True
    elif "already exists" in result["message"].lower():
        return "User already exists"
    else:
        return False

def get_all_therapists():
    users = get_all_users()
    return [user for user in users if user.get('UserRole') == 'THERAPIST' and user.get('Approved', False)]

def get_pending_therapists():
    users = get_all_users()
    return [user for user in users if user.get('UserRole') == 'THERAPIST' and not user.get('Approved', False)]

def approve_therapist_user(email):
    return update_user_approval(email, True)

def assign_therapist_to_child(child_id, therapist_id, therapist_name):
    from database.children import assign_therapist_to_child as db_assign_therapist_to_child
    return db_assign_therapist_to_child(child_id, therapist_id, therapist_name)

def authenticate_user_service(email, password):
    user = authenticate_user(email, password)
    if user:
        return user, None
    return None, "Invalid email or password."

def get_user_by_id(user_id):
    response = users_table.scan(
        FilterExpression="UserID = :id_val",
        ExpressionAttributeValues={":id_val": user_id}
    )
    items = response.get('Items', [])
    if items:
        return items[0]
    return None

def delete_user(email):
    user = get_user_by_email(email)
    if not user:
        return False
    users_table.delete_item(Key={'UserID': user['UserID']})
    return True

def update_user(user_id, updates):
    """
    Update user fields. updates is a dict of field: value
    """
    update_expression = "SET " + ", ".join(f"{k} = :{k}" for k in updates.keys())
    expression_values = {f":{k}": v for k, v in updates.items()}
    users_table.update_item(
        Key={'UserID': user_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values
    )
    return True

def set_logged_in_session(user_data):
    set_session(user_data)
