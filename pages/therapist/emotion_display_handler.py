"""
Robot Emotion Display Handler
Selects and manages appropriate emotion GIFs based on conversation context
IMPROVED: Better emotion detection with proper priority and context analysis
"""

import os
from pathlib import Path
import base64
import re

class EmotionDisplayHandler:
    """Manages robot emotion display selection and delivery"""
    
    # Emotion mappings
    EMOTIONS = {
        'surprise': 'surprise.gif',
        'sad': 'sad.gif',
        'mad': 'mad.gif',
        'neutral': 'neutral.gif'
    }
    
    # Emotion keyword patterns (ordered by priority)
    EMOTION_PATTERNS = {
        'mad': {
            'keywords': [
                'no no', 'stop that', 'don\'t do that', 'that\'s not right',
                'you must', 'frustrated', 'be careful', 'wait', 'hold on',
                'that\'s wrong', 'incorrect', 'not allowed', 'dangerous'
            ],
            'patterns': [
                r'\bno\s+no\b',
                r'\bstop\b.*\bthat\b',
                r'\bdon\'t\b',
                r'\bcan\'t\b.*\bthat\b'
            ]
        },
        'sad': {
            'keywords': [
                'sorry', 'sad', 'unfortunate', 'that\'s tough', 'difficult',
                'hard time', 'struggle', 'miss', 'lost', 'hurt',
                'don\'t worry', 'it\'s okay', 'understandable',
                'i understand', 'that must be', 'feel bad', 'upset',
                'crying', 'tears', 'lonely', 'scared'
            ],
            'patterns': [
                r'\bso\s+sorry\b',
                r'\bfeel\s+(?:sad|bad|upset)\b',
                r'\bmust\s+be\s+(?:hard|tough|difficult)\b',
                r'\bthat\'s\s+(?:tough|hard|sad)\b'
            ]
        },
        'surprise': {
            'keywords': [
                'great', 'awesome', 'wonderful', 'amazing', 'wow', 'love',
                'yay', 'hooray', 'excellent', 'fantastic', 'good job',
                'well done', 'perfect', 'brilliant', 'nice', 'cool',
                'really', 'whoa', 'oh my', 'incredible', 'super', 'terrific',
                'exciting', 'fun', 'happy', 'joy', 'beautiful', 'lovely',
                'impressive', 'outstanding', 'marvelous', 'splendid'
            ],
            'patterns': [
                r'\b(?:great|awesome|amazing|wonderful)\b.*!',
                r'\bgood\s+job\b',
                r'\bwell\s+done\b',
                r'\bthat\'s\s+(?:great|amazing|awesome)\b'
            ]
        }
    }
    
    # Map child emotions to robot empathy emotions
    CHILD_EMOTION_MAP = {
        'sad': 'sad',           # Mirror sadness
        'crying': 'sad',
        'upset': 'sad',
        'frustrated': 'sad',
        'angry': 'mad',         # Show concern
        'mad': 'mad',
        'happy': 'surprise',    # Show excitement
        'excited': 'surprise',
        'joyful': 'surprise',
        'surprised': 'surprise',
        'shy': 'neutral',       # Stay calm/welcoming
        'nervous': 'neutral',
        'disengaged': 'neutral',
        'calm': 'neutral',
        'neutral': 'neutral'
    }
    
    # Map robot actions to emotions
    ACTION_EMOTION_MAP = {
        # Excited/playful actions
        'jump': 'surprise',
        'jump_forward': 'surprise',
        'twist': 'surprise',
        'handshake': 'surprise',
        'wave': 'surprise',
        'bow': 'surprise',
        'push_up': 'surprise',
        'dig': 'surprise',
        'dance': 'surprise',
        
        # Scared/worried actions
        'scared': 'sad',
        'jump_backward': 'sad',

        # Corrective actions
        'stop': 'mad',
        'block': 'mad',
        
        # Neutral/calm actions
        'sit': 'neutral',
        'steady': 'neutral',
        'stay_low': 'neutral',
        'sleep': 'neutral',
    }
    
    def __init__(self, emotion_folder: str = "LLM_Emotion_Display"):
        """
        Initialize emotion display handler
        
        Args:
            emotion_folder: Path to folder containing emotion GIF files
        """
        self.emotion_folder = Path(emotion_folder)
        
        # Verify folder exists
        if not self.emotion_folder.exists():
            raise FileNotFoundError(f"Emotion folder not found: {emotion_folder}")
        
        # Verify all emotion files exist
        missing_files = []
        for emotion, filename in self.EMOTIONS.items():
            if not (self.emotion_folder / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            print(f"⚠️ Warning: Missing emotion files: {missing_files}")
    
    def _normalize_emotion(self, emotion: str) -> str:
        """Normalize emotion string to match available emotions"""
        if not emotion:
            return 'neutral'
        
        emotion_lower = emotion.lower().strip()
        
        # Direct match
        if emotion_lower in self.EMOTIONS:
            return emotion_lower
        
        # Map common variations
        if emotion_lower in self.CHILD_EMOTION_MAP:
            return self.CHILD_EMOTION_MAP[emotion_lower]
        
        # Default to neutral
        return 'neutral'
    
    def _check_emotion_patterns(self, text: str, emotion: str) -> bool:
        """
        Check if text matches emotion patterns
        
        Args:
            text: Text to analyze
            emotion: Emotion to check for
            
        Returns:
            True if emotion pattern is found
        """
        if emotion not in self.EMOTION_PATTERNS:
            return False
        
        text_lower = text.lower()
        patterns = self.EMOTION_PATTERNS[emotion]
        
        # Check keywords
        for keyword in patterns['keywords']:
            if keyword in text_lower:
                return True
        
        # Check regex patterns
        for pattern in patterns['patterns']:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _count_exclamations(self, text: str) -> int:
        """Count exclamation marks in text"""
        return text.count('!')
    
    def _count_questions(self, text: str) -> int:
        """Count question marks in text"""
        return text.count('?')
    
    def select_emotion(self, agent_response: str, context: dict = None) -> str:
        """
        Select emotion based on agent response and conversation context
        
        Priority order:
        1. Child's detected emotion (empathy)
        2. Critical safety/correction indicators (mad)
        3. Robot's physical action
        4. Emotional content of response text
        5. Punctuation/enthusiasm indicators
        6. Default to neutral
        
        Args:
            agent_response: The agent's text response
            context: Dictionary containing:
                - detected_emotion: Child's current emotion
                - robot_action: Robot's planned action
                - previous_emotion: Previous emotion state
                
        Returns:
            Emotion name (surprise, sad, mad, neutral)
        """
        print(f"\n🎭 === EMOTION SELECTION START ===")
        print(f"Response: {agent_response[:100]}...")
        print(f"Context: {context}")
        
        # Initialize variables
        response_lower = agent_response.lower()
        
        # PRIORITY 1: Child's Emotion (Empathy Response)
        if context:
            child_emotion = (context.get('detected_emotion') or '').lower().strip()
            
            if child_emotion:
                normalized_emotion = self._normalize_emotion(child_emotion)
                print(f"👶 Child emotion detected: '{child_emotion}' → '{normalized_emotion}'")
                
                # Strong emotions get immediate empathy response
                if child_emotion in ['sad', 'crying', 'upset', 'frustrated', 'angry', 'mad']:
                    print(f"💙 EMPATHY: Mirroring child's {child_emotion} emotion")
                    return normalized_emotion
                
                # Positive emotions get enthusiastic response
                if child_emotion in ['happy', 'excited', 'joyful']:
                    print(f"😊 JOY: Responding to child's {child_emotion} with surprise")
                    return 'surprise'
        
        # PRIORITY 2: Safety/Correction Indicators (MAD)
        if self._check_emotion_patterns(response_lower, 'mad'):
            print(f"⚠️ CORRECTION: Mad emotion indicators found")
            return 'mad'
        
        # PRIORITY 3: Robot Action
        if context and 'robot_action' in context:
            robot_action = context['robot_action']
            
            if isinstance(robot_action, dict):
                action_name = robot_action.get('action', '').lower()
            elif isinstance(robot_action, str):
                action_name = robot_action.lower()
            else:
                action_name = ''
            
            if action_name and action_name in self.ACTION_EMOTION_MAP:
                action_emotion = self.ACTION_EMOTION_MAP[action_name]
                print(f"🤖 ACTION: '{action_name}' → '{action_emotion}'")
                
                # Don't override sad/mad with neutral actions
                # But do use excited actions
                if action_emotion in ['surprise', 'sad', 'mad']:
                    return action_emotion
        
        # PRIORITY 4: Text Emotional Content
        # Check in order: sad → surprise (mad already checked above)
        
        # Check for sadness/sympathy
        if self._check_emotion_patterns(response_lower, 'sad'):
            print(f"😢 TEXT: Sad emotion patterns found")
            return 'sad'
        
        # Check for excitement/positive
        if self._check_emotion_patterns(response_lower, 'surprise'):
            print(f"😃 TEXT: Positive emotion patterns found")
            return 'surprise'
        
        # PRIORITY 5: Punctuation Analysis
        exclamations = self._count_exclamations(agent_response)
        questions = self._count_questions(agent_response)
        
        # Multiple exclamations = excitement
        if exclamations >= 2:
            print(f"❗ PUNCTUATION: {exclamations} exclamations → surprise")
            return 'surprise'
        
        # Single exclamation with positive context
        if exclamations == 1 and len(agent_response.split()) < 10:
            print(f"❗ PUNCTUATION: Short excited response → surprise")
            return 'surprise'
        
        # PRIORITY 6: Default
        print(f"😐 DEFAULT: No specific emotion detected → neutral")
        return 'neutral'
    
    def get_emotion_path(self, emotion: str) -> Path:
        """
        Get full path to emotion GIF file
        
        Args:
            emotion: Emotion name (surprise, sad, mad, neutral)
            
        Returns:
            Path to GIF file
        """
        emotion = self._normalize_emotion(emotion)
        
        if emotion not in self.EMOTIONS:
            print(f"⚠️ Unknown emotion '{emotion}', defaulting to neutral")
            emotion = 'neutral'
        
        return self.emotion_folder / self.EMOTIONS[emotion]
    
    def get_emotion_base64(self, emotion: str) -> str:
        """Get base64 encoded GIF data"""
        filepath = self.get_emotion_path(emotion)
        
        try:
            with open(filepath, 'rb') as f:
                gif_bytes = f.read()
                return base64.b64encode(gif_bytes).decode('utf-8')
        except Exception as e:
            print(f"❌ Error reading emotion file: {e}")
            # Return neutral as fallback
            try:
                neutral_path = self.emotion_folder / self.EMOTIONS['neutral']
                with open(neutral_path, 'rb') as f:
                    gif_bytes = f.read()
                    return base64.b64encode(gif_bytes).decode('utf-8')
            except:
                return ""
    
    def create_emotion_html(self, emotion: str, width: int = 200, height: int = 200) -> str:
        """
        Create HTML for displaying emotion GIF
        
        Args:
            emotion: Emotion name
            width: Display width in pixels
            height: Display height in pixels
            
        Returns:
            HTML string with embedded GIF
        """
        base64_data = self.get_emotion_base64(emotion)
        
        if not base64_data:
            return ""
        
        return f"""
        <div style="text-align: center; margin: 20px 0;">
            <img src="data:image/gif;base64,{base64_data}" 
                 width="{width}" 
                 height="{height}"
                 style="border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"
                 alt="Robot emotion: {emotion}">
        </div>
        """
    
    def get_emotion_for_action(self, robot_action: dict) -> str:
        """
        Map robot action to appropriate emotion display
        DEPRECATED: Use select_emotion() with context instead
        
        Args:
            robot_action: Dict with 'action' and 'reason'
            
        Returns:
            Emotion name
        """
        if not robot_action:
            return 'neutral'
        
        action = robot_action.get('action', '').lower()
        
        return self.ACTION_EMOTION_MAP.get(action, 'neutral')