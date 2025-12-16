"""
AWS DynamoDB Handler for storing screening sessions and managing children
Enhanced with better error handling
UPDATED: Added therapist filtering for children list
UPDATED: Added audio completion tracking methods
UPDATED: Added session counter per child
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
from decimal import Decimal
import uuid
import agent_settings


class DatabaseHandler:
    """Handle DynamoDB operations for screening sessions and children"""
    
    def __init__(self):
        try:
            # Initialize DynamoDB client
            self.dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=agent_settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=agent_settings.AWS_SECRET_ACCESS_KEY,
                region_name=agent_settings.AWS_REGION
            )
            
            # Sessions table
            self.sessions_table_name = agent_settings.DYNAMODB_SESSIONS_TABLE_NAME
            self.sessions_table = self.dynamodb.Table(self.sessions_table_name)
            
            # Children table
            self.children_table_name = agent_settings.DYNAMODB_CHILDREN_TABLE_NAME
            self.children_table = self.dynamodb.Table(self.children_table_name)
            
            # Messages table
            self.messages_table_name = agent_settings.DYNAMODB_MESSAGES_TABLE_NAME
            self.messages_table = self.dynamodb.Table(self.messages_table_name)
            
            self.users_table = self.dynamodb.Table('users')

            # Test connection
            self.sessions_table.load()
            self.children_table.load()
            self.messages_table.load()
            print(f"✅ DynamoDB connected successfully")
            
        except Exception as e:
            print(f"X DynamoDB connection failed: {e}")
            self.sessions_table = None
            self.children_table = None
            self.messages_table = None
    
    def _python_to_dynamodb(self, obj):
        """Convert Python types to DynamoDB compatible types"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._python_to_dynamodb(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._python_to_dynamodb(item) for item in obj]
        return obj
    
    def _dynamodb_to_python(self, obj):
        """Convert DynamoDB Decimal types back to Python types"""
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        elif isinstance(obj, dict):
            return {k: self._dynamodb_to_python(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._dynamodb_to_python(item) for item in obj]
        return obj
    
    # ==================== CHILDREN OPERATIONS ====================
    
    def get_all_children(self, therapist_id: str = None):
        """
        Get all children for dropdown selection
        
        Args:
            therapist_id: If provided, only return children assigned to this therapist
        
        Returns:
            List of children dictionaries
        """
        if not self.children_table:
            return []
        
        try:
            if therapist_id:
                # Filter children by TherapistID
                print(f"🔍 Fetching children for therapist: {therapist_id}")
                
                # Try using GSI if available, otherwise use scan with filter
                try:
                    # Attempt to use GSI (if TherapistID-index exists)
                    response = self.children_table.query(
                        IndexName='TherapistID-index',
                        KeyConditionExpression=Key('TherapistID').eq(therapist_id)
                    )
                    children = response.get('Items', [])
                    print(f"✅ Found {len(children)} children using GSI")
                except Exception as gsi_error:
                    print(f"⚠️ GSI not available, using scan: {gsi_error}")
                    # Fallback to scan with filter
                    response = self.children_table.scan(
                        FilterExpression=Attr('TherapistID').eq(therapist_id)
                    )
                    children = response.get('Items', [])
                    print(f"✅ Found {len(children)} children using scan")
            else:
                # Get all children (admin view)
                print(f"🔍 Fetching all children")
                response = self.children_table.scan()
                children = response.get('Items', [])
            
            # Sort by name
            children.sort(key=lambda x: x.get('Name', x.get('name', '')))
            
            result = [self._dynamodb_to_python(child) for child in children]
            
            if result:
                print(f"📋 Children list:")
                for child in result:
                    print(f"   - {child.get('Name', child.get('name', 'Unknown'))} (ID: {child.get('ChildID', child.get('child_id', 'N/A'))})")
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting children: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_child(self, child_id: str):
        """Get specific child information"""
        if not self.children_table:
            return None
        
        try:
            # Try with ChildID first
            response = self.children_table.get_item(Key={'ChildID': child_id})
            
            if 'Item' in response:
                return self._dynamodb_to_python(response['Item'])
            
            # Fallback to child_id
            response = self.children_table.get_item(Key={'child_id': child_id})
            
            if 'Item' in response:
                return self._dynamodb_to_python(response['Item'])
            
            return None
            
        except Exception as e:
            print(f"Error getting child: {e}")
            return None
    
    # ==================== SESSION OPERATIONS ====================
    
    def _get_next_session_number(self, child_id: str) -> int:
        """
        Get the next session number for a specific child
        
        Args:
            child_id: The child's ID
            
        Returns:
            Next session number (1 for first session, 2 for second, etc.)
        """
        if not self.sessions_table:
            return 1
        
        try:
            # Try to query using GSI if available
            try:
                response = self.sessions_table.query(
                    IndexName='child_id-created_at-index',
                    KeyConditionExpression=Key('child_id').eq(child_id),
                    ScanIndexForward=False,  # Sort descending
                    Limit=1
                )
                items = response.get('Items', [])
            except Exception as gsi_error:
                print(f"⚠️ GSI not available for session count, using scan: {gsi_error}")
                # Fallback to scan
                response = self.sessions_table.scan(
                    FilterExpression=Attr('child_id').eq(child_id)
                )
                items = response.get('Items', [])
            
            if not items:
                # First session for this child
                return 1
            
            # Find the highest session number
            max_session_num = 0
            for item in items:
                session_num = item.get('session_number', 0)
                if isinstance(session_num, Decimal):
                    session_num = int(session_num)
                max_session_num = max(max_session_num, session_num)
            
            return max_session_num + 1
            
        except Exception as e:
            print(f"⚠️ Error calculating session number: {e}")
            import traceback
            traceback.print_exc()
            # Default to 1 on error
            return 1
    
    def create_session(self, session_id: str, child_id: str, 
                      clinician_id: str, metadata: dict = None) -> bool:
        """
        Create a new screening session
        
        Args:
            session_id: Unique session identifier
            child_id: ID of the child being screened
            clinician_id: ID of the therapist/clinician (REQUIRED)
            metadata: Additional session metadata
        
        Returns:
            True if successful, False otherwise
        """
        if not self.sessions_table:
            print("❌ Sessions table not initialized")
            return False
        
        if not clinician_id:
            print("❌ clinician_id is required but was not provided")
            return False
        
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # Get child information
            child = self.get_child(child_id)
            child_name = child.get('Name', child.get('name', 'Unknown')) if child else 'Unknown'
            
            # Calculate session number for this child
            session_number = self._get_next_session_number(child_id)
            
            item = {
                'session_id': session_id,
                'child_id': child_id,
                'child_name': child_name,
                'clinician_id': clinician_id,  # No fallback - must be valid
                'session_number': session_number,  # NEW: Session counter per child
                'created_at': timestamp,
                'status': 'active',
                'metadata': metadata or {}
            }
            
            item = self._python_to_dynamodb(item)
            self.sessions_table.put_item(Item=item)
            
            print(f"✅ Session created: {session_id}")
            print(f"   Child: {child_name} ({child_id})")
            print(f"   Session Number: #{session_number}")
            print(f"   Clinician/Therapist: {clinician_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_session_metadata(self, session_id: str, metadata_updates: dict) -> bool:
        """
        Update session metadata fields
        
        Args:
            session_id: Session ID to update
            metadata_updates: Dictionary of metadata fields to update
            
        Returns:
            True if successful, False otherwise
        """
        if not self.sessions_table:
            print("❌ Sessions table not initialized")
            return False
        
        try:
            # First get the current session to get existing metadata
            response = self.sessions_table.get_item(Key={'session_id': session_id})
            
            if 'Item' not in response:
                print(f"❌ Session {session_id} not found")
                return False
            
            current_metadata = response['Item'].get('metadata', {})
            
            # Merge with new updates
            updated_metadata = {**current_metadata, **metadata_updates}
            updated_metadata = self._python_to_dynamodb(updated_metadata)
            
            # Update the session
            self.sessions_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET metadata = :metadata',
                ExpressionAttributeValues={
                    ':metadata': updated_metadata
                }
            )
            
            print(f"✅ Session metadata updated: {session_id}")
            print(f"   Updates: {metadata_updates}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating session metadata: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def signal_audio_playing(self, session_id: str) -> bool:
        """Signal that audio is currently playing in child interface"""
        return self.update_session_metadata(session_id, {'audio_playing': True})
    
    def signal_audio_complete(self, session_id: str) -> bool:
        """Signal that audio playback has completed in child interface"""
        return self.update_session_metadata(session_id, {'audio_playing': False})
    
    def is_audio_playing(self, session_id: str) -> bool:
        """Check if audio is currently playing"""
        try:
            response = self.sessions_table.get_item(Key={'session_id': session_id})
            if 'Item' in response:
                metadata = response['Item'].get('metadata', {})
                return metadata.get('audio_playing', False)
            return False
        except Exception as e:
            print(f"❌ Error checking audio status: {e}")
            return False
    
    def end_session(self, session_id: str):
        """Mark session as completed"""
        if not self.sessions_table:
            print("❌ Sessions table not initialized")
            return False
        
        try:
            timestamp = datetime.utcnow().isoformat()
            
            self.sessions_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET #status = :status, ended_at = :ended_at',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'completed',
                    ':ended_at': timestamp
                }
            )
            
            print(f"✅ Session ended: {session_id} at {timestamp}")
            return True
            
        except Exception as e:
            print(f"❌ Error ending session: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_session(self, session_id: str):
        """Retrieve a session with its messages"""
        if not self.sessions_table:
            return None
        
        try:
            response = self.sessions_table.get_item(Key={'session_id': session_id})
            
            if 'Item' in response:
                session = self._dynamodb_to_python(response['Item'])
                
                # Get messages for this session
                messages = self.get_session_messages(session_id)
                session['messages'] = messages
                
                return session
            return None
            
        except Exception as e:
            print(f"Error retrieving session: {e}")
            return None
    
    def get_all_sessions(self, limit: int = 5000):
        """Get all sessions (most recent first)"""
        if not self.sessions_table:
            return []
        
        try:
            response = self.sessions_table.scan(Limit=limit)
            items = response.get('Items', [])
            
            items = [self._dynamodb_to_python(item) for item in items]
            items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return items
            
        except Exception as e:
            print(f"Error retrieving sessions: {e}")
            return []
    
    # ==================== MESSAGE OPERATIONS ====================
    
    def add_message(self, session_id: str, role: str, content: str, metadata: dict = None):
        """
        Add a message to the messages table
        IMPROVED: Preserves all emotion and context metadata INCLUDING robot_action
        """
        if not self.messages_table:
            print("❌ Messages table not initialized")
            return False
        
        try:
            # Generate unique message_id
            message_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            message = {
                'message_id': message_id,
                'session_id': session_id,
                'timestamp': timestamp,
                'role': role,
                'content': content
            }
            
            # CRITICAL: Keep ALL metadata INCLUDING robot_action
            if metadata:
                # Only exclude truly internal fields
                exclude_fields = {'raw_response', 'debug_info', 'internal_state'}
                
                filtered_metadata = {
                    k: v for k, v in metadata.items() 
                    if k not in exclude_fields
                }
                
                if filtered_metadata:
                    message['metadata'] = filtered_metadata
                    
                    print(f"📦 Storing metadata: {list(filtered_metadata.keys())}")
                    
                    # Log important fields
                    if 'detected_emotion' in filtered_metadata:
                        print(f"   👶 Child emotion: {filtered_metadata['detected_emotion']}")
                    if 'robot_action' in filtered_metadata:
                        action = filtered_metadata['robot_action']
                        if isinstance(action, dict):
                            print(f"   🤖 Robot action: {action.get('action', 'N/A')}")
                        else:
                            print(f"   🤖 Robot action (raw): {action}")
                    if 'emotion' in filtered_metadata:
                        print(f"   🎭 Selected emotion: {filtered_metadata['emotion']}")
            
            message = self._python_to_dynamodb(message)
            
            print(f"💾 Saving message to DynamoDB:")
            print(f"   Session: {session_id}")
            print(f"   Role: {role}")
            print(f"   Content: {content[:50]}...")
            
            self.messages_table.put_item(Item=message)
            
            print(f"✅ Message saved successfully: {message_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding message: {e}")
            import traceback
            traceback.print_exc()
            return False
            
            try:
                # Generate unique message_id
                message_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                
                message = {
                    'message_id': message_id,
                    'session_id': session_id,
                    'timestamp': timestamp,
                    'role': role,
                    'content': content
                }
                
                # Only store non-robot-action metadata
                if metadata:
                    filtered_metadata = {k: v for k, v in metadata.items() if k != 'robot_action'}
                    if filtered_metadata:
                        message['metadata'] = filtered_metadata
                
                message = self._python_to_dynamodb(message)
                
                print(f"💾 Saving message to DynamoDB:")
                print(f"   Session: {session_id}")
                print(f"   Role: {role}")
                print(f"   Content: {content[:50]}...")
                
                self.messages_table.put_item(Item=message)
                
                print(f"✅ Message saved successfully: {message_id}")
                return True
                
            except Exception as e:
                print(f"❌ Error adding message: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def get_session_messages(self, session_id: str):
        """Get all messages for a session"""
        if not self.messages_table:
            print("❌ Messages table not initialized")
            return []
        
        try:
            print(f"🔍 Querying messages for session: {session_id}")
            
            # Try using GSI first
            try:
                response = self.messages_table.query(
                    IndexName='session_id-timestamp-index',
                    KeyConditionExpression=Key('session_id').eq(session_id)
                )
                messages = response.get('Items', [])
                print(f"✅ Found {len(messages)} messages using GSI for session {session_id}")
            except Exception as gsi_error:
                print(f"⚠️ GSI query failed (index may not exist): {gsi_error}")
                print(f"   Falling back to scan...")
                
                # Fallback to scan if GSI doesn't exist
                response = self.messages_table.scan(
                    FilterExpression=Attr('session_id').eq(session_id)
                )
                messages = response.get('Items', [])
                print(f"✅ Found {len(messages)} messages using scan for session {session_id}")
                
                # Sort manually by timestamp
                messages.sort(key=lambda x: x.get('timestamp', ''))
            
            result = [self._dynamodb_to_python(msg) for msg in messages]
            
            if result:
                print(f"   📋 Messages for session {session_id}:")
                for idx, msg in enumerate(result):
                    print(f"      {idx+1}. [{msg.get('role')}] {msg.get('content')[:40]}... (ID: {msg.get('message_id')[:8]}...)")
            else:
                print(f"   📋 No messages found for session {session_id}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error getting messages: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # ==================== CLINICIAN NOTES ====================
    
    def add_clinician_note(self, session_id: str, note: str):
        """Add a clinician observation note"""
        if not self.sessions_table:
            return False
        
        try:
            response = self.sessions_table.get_item(Key={'session_id': session_id})
            
            if 'Item' not in response:
                print(f"Session {session_id} not found")
                return False
            
            item = response['Item']
            notes = item.get('clinician_notes', [])
            
            note_item = {
                'note': note,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            notes.append(note_item)
            
            self.sessions_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET clinician_notes = :notes',
                ExpressionAttributeValues={':notes': notes}
            )
            
            print(f"✅ Note added to session: {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding note: {e}")
            return False
        
    def get_parent_name(self, parent_id):
        """Fetch parent FullName from users table using ParentID (which is UserID)"""
        if not self.users_table or not parent_id:
            return "Unknown"
        
        try:
            # Assuming UserID is the Primary Key in 'users' table
            response = self.users_table.get_item(Key={'UserID': parent_id})
            
            if 'Item' in response:
                return response['Item'].get('FullName', 'Unknown')
            return "Unknown"
        except Exception as e:
            print(f"Error fetching parent name: {e}")
            return "Error"


"""
OPTIONAL: Add helper method to extract emotion context from message

Add this method to your DatabaseHandler class to help retrieve 
emotion context when needed:
"""

def get_message_emotion_context(self, message_id: str) -> dict:
    """
    Get emotion context from a specific message
    
    Args:
        message_id: The message ID to retrieve context from
        
    Returns:
        Dictionary with emotion context:
        - detected_emotion: Child's emotion
        - robot_action: Robot's action
        - emotion: Selected display emotion
    """
    if not self.messages_table:
        return {}
    
    try:
        response = self.messages_table.get_item(Key={'message_id': message_id})
        
        if 'Item' not in response:
            return {}
        
        message = self._dynamodb_to_python(response['Item'])
        metadata = message.get('metadata', {})
        
        return {
            'detected_emotion': metadata.get('detected_emotion', 'neutral'),
            'robot_action': metadata.get('robot_action', {}),
            'emotion': metadata.get('emotion', 'neutral'),
            'content': message.get('content', '')
        }
        
    except Exception as e:
        print(f"❌ Error getting emotion context: {e}")
        return {}


def get_conversation_emotion_flow(self, session_id: str) -> list:
    """
    Get the flow of emotions throughout a conversation
    Useful for analysis and debugging
    
    Args:
        session_id: Session ID
        
    Returns:
        List of dictionaries with emotion flow
    """
    messages = self.get_session_messages(session_id)
    
    emotion_flow = []
    
    for idx, msg in enumerate(messages):
        if msg.get('role') == 'assistant':
            metadata = msg.get('metadata', {})
            
            emotion_flow.append({
                'message_number': idx + 1,
                'content_preview': msg.get('content', '')[:50],
                'detected_child_emotion': metadata.get('detected_emotion', 'N/A'),
                'robot_action': metadata.get('robot_action', {}).get('action', 'N/A'),
                'displayed_emotion': metadata.get('emotion', 'N/A'),
                'timestamp': msg.get('timestamp', '')
            })
    
    return emotion_flow