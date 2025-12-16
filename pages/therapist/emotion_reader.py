"""
Emotion Reader - Fetch real-time child emotions from DynamoDB
Integrates with EmotiBit system
"""

import boto3
from datetime import datetime, timedelta
import agent_settings


class EmotionReader:
    """Read emotion data from DynamoDB Emotion table"""
    
    def __init__(self):
        try:
            self.dynamodb = boto3.resource(
                'dynamodb',
                aws_access_key_id=agent_settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=agent_settings.AWS_SECRET_ACCESS_KEY,
                region_name=agent_settings.AWS_REGION
            )
            
            self.emotion_table_name = agent_settings.DYNAMODB_EMOTION_TABLE_NAME
            self.emotion_table = self.dynamodb.Table(self.emotion_table_name)
            
            # Test connection
            self.emotion_table.load()
            print(f"✅ Emotion table connected: {self.emotion_table_name}")
            
        except Exception as e:
            print(f"❌ Emotion table connection failed: {e}")
            self.emotion_table = None
    
    def get_current_emotion(self, session_id: str, time_window_seconds: int = 30):
        """
        Get the most recent emotion for a session within time window
        
        Args:
            session_id: Current session ID
            time_window_seconds: Only consider emotions from last N seconds (default: 30)
            
        Returns:
            dict with 'emotion' and 'timestamp', or None if no recent emotion found
        """
        if not self.emotion_table:
            print("❌ Emotion table not initialized")
            return None
        
        try:
            # Calculate time threshold
            time_threshold = (datetime.now() - timedelta(seconds=time_window_seconds)).isoformat()
            
            print(f"🔍 Querying emotions for session: {session_id}")
            print(f"   Time window: last {time_window_seconds} seconds")
            
            # Query emotions for this session
            response = self.emotion_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
                ScanIndexForward=False,  # Get most recent first
                Limit=10  # Get last 10 emotions
            )
            
            items = response.get('Items', [])
            
            if not items:
                print(f"   ℹ️ No emotions found for session {session_id}")
                return None
            
            # Filter by time window and get most recent
            recent_emotions = [
                item for item in items 
                if item.get('timestamp', '') >= time_threshold
            ]
            
            if not recent_emotions:
                print(f"   ℹ️ No emotions within last {time_window_seconds} seconds")
                return None
            
            # Get most recent emotion
            latest = recent_emotions[0]
            emotion = latest.get('emotion', 'unknown')
            timestamp = latest.get('timestamp', '')
            
            print(f"   ✅ Current emotion: {emotion} (at {timestamp})")
            
            return {
                'emotion': emotion,
                'timestamp': timestamp
            }
            
        except Exception as e:
            print(f"❌ Error getting emotion: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_emotion_history(self, session_id: str, limit: int = 50):
        """
        Get emotion history for a session
        
        Args:
            session_id: Session ID
            limit: Maximum number of emotions to retrieve
            
        Returns:
            List of emotion records sorted by timestamp (newest first)
        """
        if not self.emotion_table:
            return []
        
        try:
            response = self.emotion_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
                ScanIndexForward=False,  # Newest first
                Limit=limit
            )
            
            items = response.get('Items', [])
            print(f"📊 Retrieved {len(items)} emotion records for session {session_id}")
            
            return items
            
        except Exception as e:
            print(f"❌ Error getting emotion history: {e}")
            return []
    
    def get_emotion_summary(self, session_id: str):
        """
        Get emotion summary statistics for a session
        
        Returns:
            dict with emotion counts and percentages
        """
        history = self.get_emotion_history(session_id)
        
        if not history:
            return None
        
        from collections import Counter
        emotion_counts = Counter([item['emotion'] for item in history])
        total = len(history)
        
        summary = {
            'total_readings': total,
            'emotions': {
                emotion: {
                    'count': count,
                    'percentage': round((count / total) * 100, 1)
                }
                for emotion, count in emotion_counts.items()
            },
            'dominant_emotion': emotion_counts.most_common(1)[0][0] if emotion_counts else None
        }
        
        return summary