"""
Language Screening Agent with Picture Description Support
UPDATED: Includes picture prompt feature for eliciting descriptive language
"""

from langchain.chat_models import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import agent_settings
import time
import json
from emotion_display_handler import EmotionDisplayHandler
from emotion_reader import EmotionReader
from picture_handler import PictureHandler

class LanguageScreeningAgent:
    """Conversational agent for language screening with clinical tracking, robot actions, and emotion display"""
    
    def __init__(self):
        # Load system prompt
        with open(agent_settings.SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=agent_settings.OPENAI_API_KEY,
            model=agent_settings.OPENAI_MODEL,
            temperature=agent_settings.TEMPERATURE
        )
        
        # Initialize emotion display handler
        try:
            self.emotion_handler = EmotionDisplayHandler()
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize emotion handler: {e}")
            self.emotion_handler = None
        
        # Initialize emotion reader for database
        self.emotion_reader = EmotionReader()

        # NEW: Initialize picture handler
        self.picture_handler = PictureHandler()
        
        # Conversation tracking
        self.messages = []
        self.child_responses = []  # Track child responses for picture timing
        self.last_response_time = None
        self.conversation_turn = 0

        # Picture tracking
        self.current_picture_active = False
        self.picture_followups_count = 0
        
        # Question type tracking for variety
        self.question_types_used = {
            'open': 0,
            'closed': 0,
            'choice': 0,
            'descriptive': 0,
            'picture': 0
        }
        
        # Robot action tracking
        self.last_robot_action = None
        self.robot_actions_performed = []
        self.current_session_id = None
        self.child_age = None

    def set_session_id(self, session_id: str):
        """Set the current session ID for emotion tracking"""
        self.current_session_id = session_id
        print(f"🎯 Agent tracking session: {session_id}")

        # Reset picture handler for new session
        self.picture_handler.reset()
  
    def detect_child_robot_command(self, user_input: str) -> dict:
        """
        Detect if child is giving a direct robot command
        
        Args:
            user_input: Child's speech input
            
        Returns:
            dict with 'is_command', 'action', 'original_text'
        """
        user_lower = user_input.lower().strip()
        
        # Define command patterns
        command_patterns = {
            'bow': ['bow', 'take a bow'],
            'handshake': ['handshake', 'shake hands', 'shake hand', 'give me five', 'high five'],
            'wave': ['wave', 'say hi', 'say hello', 'wave hello'],
            'jump': ['jump', 'jump up'],
            'jump_forward': ['jump forward', 'hop forward'],
            'jump_backward': ['jump backward', 'jump back', 'hop back'],
            'twist': ['twist', 'dance', 'wiggle'],
            'sit': ['sit', 'sit down'],
            'stay_low': ['stay low', 'crouch', 'get low', 'go down'],
            'push_up': ['push up', 'pushup', 'do pushups', 'exercise'],
            'dig': ['dig', 'scratch'],
            'scared': ['be scared', 'act scared', 'shiver'],
            'sleep': ['sleep', 'go to sleep', 'take a nap'],
            'steady': ['stand up', 'steady', 'balance']
        }
        
        # Check if input matches any command
        for action, patterns in command_patterns.items():
            for pattern in patterns:
                if pattern in user_lower:
                    print(f"🎯 Child command detected: '{user_input}' → {action}")
                    return {
                        'is_command': True,
                        'action': action,
                        'original_text': user_input
                    }
        
        return {
            'is_command': False,
            'action': None,
            'original_text': user_input
        }
    
    def get_current_emotion_context(self) -> str:
        """
        Get current child emotion from database and format it for LLM context
        
        Returns:
            str: Formatted emotion context for the LLM
        """
        if not self.current_session_id:
            return ""
        
        # Fetch emotion from database
        emotion_data = self.emotion_reader.get_current_emotion(
            self.current_session_id,
            time_window_seconds=30  # Consider emotions from last 30 seconds
        )
        
        if not emotion_data:
            return "\n[EMOTION STATUS: No recent emotion data available]"
        
        emotion = emotion_data['emotion']
        timestamp = emotion_data['timestamp']
        
        # Map emotions to guidance for the LLM
        emotion_guidance = {
            'happy': "Child is currently feeling happy and engaged. Continue with positive reinforcement.",
            'sad': "Child appears sad. Use extra encouragement and gentleness. Consider simpler questions.",
            'angry': "Child may be frustrated. Be patient, use calming language, offer breaks if needed.",
            'surprised': "Child is surprised or curious. Good opportunity for engagement.",
            'neutral': "Child is calm and neutral. Proceed normally with the screening.",
            'fear': "Child appears anxious or fearful. Use very gentle, reassuring language. Slow down.",
            'disgust': "Child may be uncomfortable. Check if they need a break or change of topic."
        }
        
        guidance = emotion_guidance.get(emotion.lower(), "Child's emotional state detected.")
        
        emotion_context = f"""

[REAL-TIME EMOTION DETECTED FROM EMOTIBIT]
Current Emotion: {emotion}
Timestamp: {timestamp}
Guidance: {guidance}

IMPORTANT: Adapt your response based on the child's emotional state. Be empathetic and responsive to their feelings.
"""
        return emotion_context
    
    def should_show_picture_now(self) -> bool:
        """
        Decide if it's appropriate to show a picture now
        
        Returns:
            True if picture should be shown
        """
        # Don't show if already showing one
        if self.current_picture_active:
            return False
        
        # Use picture handler's logic
        return self.picture_handler.should_show_picture(
            self.conversation_turn,
            self.child_responses
        )
    
    def start_conversation(self) -> dict:
        """
        Get initial greeting from agent with emotion
        UPDATED: Includes emotion context from database
        """
        # Get emotion context from database
        emotion_context = self.get_current_emotion_context()
        
        # ===== STRENGTHEN THE PROMPT =====
        greeting_prompt = """Start the screening conversation. Greet the child warmly and ask their name.

    CRITICAL: You MUST include a robot action using ONLY these valid actions:
    bow, handshake, wave, jump, jump_forward, jump_backward, twist, sit, stay_low, push_up, dig, scared, sleep, steady

    For the greeting, use 'wave' or 'bow'.

    DO NOT use: smile, nod, laugh, clap - these actions DO NOT EXIST in the robot.

    Format:
    Your greeting text.

    ROBOT_ACTION: {"action": "wave", "reason": "greeting the child"}

    This is MANDATORY."""
        # ===== END STRENGTHENED PROMPT =====
        
        # Add emotion context if available
        if emotion_context:
            greeting_prompt += emotion_context
        
        response = self.llm.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=greeting_prompt)
        ])
        
        greeting = response.content
        
        print(f"🤖 LLM Response (raw): {greeting[:200]}...")
        
        # Extract robot action if present
        robot_action = self._extract_robot_action(greeting)
        clean_text = self._clean_robot_action_from_text(greeting)
        
        print(f"🧹 Cleaned text: {clean_text[:100]}...")
        print(f"🎯 Robot action: {robot_action}")
        
        # MANDATORY: Ensure we have a greeting action
        if not robot_action:
            print(f"⚠️ WARNING: LLM did not provide robot action. Using default 'wave'")
            robot_action = {
                "action": "wave",
                "reason": "greeting the child for first time (fallback)"
            }
        
        # Validate that clean_text is not empty
        if not clean_text or clean_text.strip() == "":
            print(f"⚠️ WARNING: Cleaned text is empty! Using raw response.")
            clean_text = greeting.replace("ROBOT_ACTION:", "").strip()
            if "{" in clean_text:
                json_start = clean_text.find("{")
                json_end = clean_text.find("}", json_start)
                if json_end != -1:
                    clean_text = clean_text[:json_start].strip() + " " + clean_text[json_end+1:].strip()
            clean_text = clean_text.strip()
        
        # Select emotion display
        emotion = self._select_emotion_display(clean_text, robot_action, None)
        
        self.messages.append({"role": "assistant", "content": clean_text})
        self.last_response_time = time.time()
        self.conversation_turn = 1
        
        return {
            "response": clean_text,
            "robot_action": robot_action,
            "emotion": emotion,
            "picture": None
        }
    
    def chat(self, user_input: str, response_time: float = None) -> dict:
        """
        Process user input and return agent response with robot action and emotion
        UPDATED: Includes emotion context from database
        
        Args:
            user_input: Child's response
            response_time: Time taken for child to respond (seconds)
            
        Returns:
            dict with 'response', 'response_time', 'robot_action', 'detected_emotion', 'emotion', 'is_child_command'
        """
        # FIRST: Check if child is giving a robot command
        command_result = self.detect_child_robot_command(user_input)
        
        if command_result['is_command']:
            # Child gave a direct robot command!
            action_name = command_result['action']
            
            print(f"🎮 CHILD COMMAND: '{user_input}' → Robot action: {action_name}")
            
            # Generate encouraging response
            encouraging_responses = [
                f"Okay! Watch this!",
                f"Sure! Here we go!",
                f"Alright! Let me do that!",
                f"You got it! Look!",
                f"Of course! Ready?"
            ]
            
            import random
            response_text = random.choice(encouraging_responses)
            
            robot_action = {
                "action": action_name,
                "reason": f"child commanded: {user_input}"
            }
            
            # Add to conversation history
            self.messages.append({
                "role": "user",
                "content": user_input,
                "is_robot_command": True
            })
            
            self.messages.append({
                "role": "assistant",
                "content": response_text,
                "is_command_response": True
            })
            
            # Select emotion (excited/happy for commands)
            emotion = "surprise"  # Robot is excited to perform
            
            return {
                "response": response_text,
                "response_time": response_time,
                "robot_action": robot_action,
                "detected_emotion": "engaged",
                "emotion": emotion,
                "picture": None,
                "is_child_command": True
            }
        
        # NORMAL CONVERSATION FLOW (not a command)
        # Detect emotion from response
        detected_emotion = self._detect_emotion(user_input)
        
        # Add user message
        self.messages.append({
            "role": "user", 
            "content": user_input,
            "response_time": response_time,
            "detected_emotion": detected_emotion
        })

        self.child_responses.append(user_input)


        # Check if we should show a picture
        picture_to_show = None

        # DEBUG: Log picture decision
        print(f"🎯 PICTURE CHECK:")
        print(f"   Turn: {self.conversation_turn}")
        print(f"   Child responses count: {len(self.child_responses)}")
        print(f"   Pictures shown: {len(self.picture_handler.pictures_shown)}/{len(self.picture_handler.available_pictures)}")
        print(f"   Current picture active: {self.current_picture_active}")

        if self.should_show_picture_now():
            picture_info = self.picture_handler.select_picture(self.child_age)
            if picture_info:
                picture_to_show = picture_info
                self.current_picture_active = True
                self.picture_followups_count = 0
                print(f"🖼️ Showing picture: {picture_info['filename']}")
        else:
            print(f"   ❌ Not showing picture yet")
        
        # Build conversation context
        llm_messages = [SystemMessage(content=self.system_prompt)]
        
        # Add conversation history (last 20 messages)
        for msg in self.messages[-20:]:
            if msg["role"] == "user":
                llm_messages.append(HumanMessage(content=msg["content"]))
            else:
                llm_messages.append(AIMessage(content=msg["content"]))

        # Add picture context if showing one
        if picture_to_show:
            picture_prompt = self.picture_handler.get_picture_prompt(picture_to_show)
            picture_instruction = f"""
IMPORTANT: A picture is now being shown to the child!

Picture: {picture_to_show['filename']}
Complexity: {picture_to_show['complexity']}
Targets: {', '.join(picture_to_show['targets'])}

Introduce the picture naturally and ask the child to describe what they see. Use a 'jump_forward' robot action to show excitement about the picture!

Your response should be something like: "{picture_prompt}"
"""
            llm_messages.append(HumanMessage(content=picture_instruction))
            self.question_types_used['picture'] += 1
        
        # Handle follow-ups for active picture
        elif self.current_picture_active:
            self.picture_followups_count += 1
            
            if self.picture_followups_count < 3:
                followup_prompts = self.picture_handler.get_followup_prompts()
                followup_instruction = f"""
The picture is still being shown. Ask a follow-up question to elicit more description.
Some suggestions: {', '.join(followup_prompts[:3])}

This is follow-up #{self.picture_followups_count}. After 2-3 exchanges, transition to a new topic.
"""
                llm_messages.append(HumanMessage(content=followup_instruction))
            else:
                # End picture task
                self.current_picture_active = False
                transition_instruction = "The child has described the picture well. Praise them and smoothly transition to a new conversational topic. The picture will be removed."
                llm_messages.append(HumanMessage(content=transition_instruction))
        
        
        # Add instruction for question variety
        instruction = self._get_next_question_instruction()
        if instruction and not picture_to_show:
            llm_messages.append(HumanMessage(content=instruction))
        
        # Add detected emotion from child's speech
        if detected_emotion != 'neutral':
            emotion_instruction = f"Note: The child seems {detected_emotion}. Adjust your response accordingly."
            llm_messages.append(HumanMessage(content=emotion_instruction))
        
        # NEW: Add real-time emotion context from database
        emotion_context = self.get_current_emotion_context()
        if emotion_context:
            llm_messages.append(HumanMessage(content=emotion_context))
        
        # Prevent repetitive robot actions
        if self.last_robot_action:
            last_action_name = self.last_robot_action.get('action')
            # ===== STRENGTHEN THIS SECTION =====
            repetition_warning = f"""CRITICAL REQUIREMENT: 

        You just used '{last_action_name}'. Choose a DIFFERENT action from this list:
        bow, handshake, wave, jump, jump_forward, jump_backward, twist, sit, stay_low, push_up, dig, scared, sleep, steady

        DO NOT use: smile, nod, laugh, clap, turn, look - THESE DO NOT EXIST!

        Format:
        Your response text.

        ROBOT_ACTION: {{"action": "different_valid_action", "reason": "explanation"}}"""
            # ===== END STRENGTHENED SECTION =====
            llm_messages.append(HumanMessage(content=repetition_warning))
        else:
            # ===== ADD VALIDATION HERE TOO =====
            mandatory_action = """CRITICAL: Include a robot action from this list ONLY:
        bow, handshake, wave, jump, jump_forward, jump_backward, twist, sit, stay_low, push_up, dig, scared, sleep, steady

        DO NOT invent actions like "smile" or "nod" - they don't exist!

        Format: ROBOT_ACTION: {"action": "valid_action", "reason": "reason"}"""
            # ===== END VALIDATION =====
            # Emphasize mandatory robot action
            llm_messages.append(HumanMessage(content="MANDATORY: Include a robot action in your response."))
        
        # Get response
        response = self.llm.invoke(llm_messages)
        agent_response = response.content
        
        # Track question type
        self._track_question_type(agent_response)
        
        # Extract robot action
        robot_action = self._extract_robot_action(agent_response)
        clean_text = self._clean_robot_action_from_text(agent_response)
        
        # MANDATORY: Ensure robot action exists
        if not robot_action:
            print(f"⚠️ WARNING: LLM did not provide robot action. Using fallback 'steady'")
            robot_action = {
                "action": "steady",
                "reason": "maintaining engagement (fallback)"
            }
        
        # Validate clean_text is not empty
        if not clean_text or clean_text.strip() == "":
            print(f"⚠️ WARNING: Cleaned text is empty in chat! Using raw response.")
            clean_text = agent_response.replace("ROBOT_ACTION:", "").strip()
            if "{" in clean_text:
                json_start = clean_text.find("{")
                json_end = clean_text.find("}", json_start)
                if json_end != -1:
                    clean_text = clean_text[:json_start].strip() + " " + clean_text[json_end+1:].strip()
            clean_text = clean_text.strip()
        
        # Select emotion display
        emotion = self._select_emotion_display(clean_text, robot_action, detected_emotion)
        
        # Track robot action
        if robot_action:
            self.last_robot_action = robot_action
            self.robot_actions_performed.append({
                'action': robot_action['action'],
                'reason': robot_action.get('reason', ''),
                'emotion': detected_emotion
            })
        
        # Add to history
        self.messages.append({"role": "assistant", "content": clean_text})
        self.last_response_time = time.time()
        self.conversation_turn += 1 
        return {
            "response": clean_text,
            "response_time": response_time,
            "robot_action": robot_action,
            "detected_emotion": detected_emotion,
            "emotion": emotion,
            "picture": picture_to_show,
            "is_child_command": False
        }
    
    def _select_emotion_display(self, response_text: str, robot_action: dict, detected_emotion: str) -> str:
        """
        Select appropriate emotion display for the response
        
        Args:
            response_text: Agent's response text
            robot_action: Robot action dict
            detected_emotion: Child's detected emotion
            
        Returns:
            Emotion name (happy, sad, mad, neutral)
        """
        if not self.emotion_handler:
            return 'neutral'
        
        context = {
            'detected_emotion': detected_emotion,
            'robot_action': robot_action
        }
        
        emotion = self.emotion_handler.select_emotion(response_text, context)
        print(f"😊 Selected emotion display: {emotion}")
        
        return emotion
    
    def _detect_emotion(self, text: str) -> str:
        """
        Detect emotion from child's response
        
        Args:
            text: Child's response text
            
        Returns:
            Detected emotion string
        """
        text_lower = text.lower()
        
        # Happy indicators
        if any(word in text_lower for word in ['yay', 'happy', 'love', 'fun', 'great', 'awesome', 'cool', 'yes!', 'yeah!']):
            return 'happy'
        
        # Excited indicators
        if any(word in text_lower for word in ['wow', 'amazing', 'exciting']) or text.count('!') >= 2:
            return 'excited'
        
        # Sad indicators
        if any(word in text_lower for word in ['sad', 'cry', 'bad', 'don\'t like', 'hate', 'no']):
            return 'sad'
        
        # Shy/uncertain indicators
        if any(word in text_lower for word in ['maybe', 'i don\'t know', 'um', 'uh', 'dunno']):
            return 'shy'
        
        # Engaged/thoughtful
        if len(text.split()) > 10:
            return 'engaged'
        
        # Short responses might indicate disengagement
        if len(text.split()) <= 2:
            return 'disengaged'
        
        return 'neutral'
    
    def _extract_robot_action(self, text: str) -> dict:
        try:
            if "ROBOT_ACTION:" in text:
                start_idx = text.find("ROBOT_ACTION:") + len("ROBOT_ACTION:")
                json_str = text[start_idx:].strip()
                
                if json_str.startswith("{"):
                    end_idx = json_str.find("}") + 1
                    json_str = json_str[:end_idx]
                    return json.loads(json_str)
        except Exception as e:
            print(f"Error extracting robot action: {e}")
        
        return None
    
    def _clean_robot_action_from_text(self, text: str) -> str:
        """Remove robot action JSON from text"""
        if "ROBOT_ACTION:" in text:
            start_idx = text.find("ROBOT_ACTION:")
            json_start = text.find("{", start_idx)
            if json_start != -1:
                json_end = text.find("}", json_start)
                if json_end != -1:
                    before_action = text[:start_idx].strip()
                    after_action = text[json_end + 1:].strip()
                    
                    if after_action:
                        return after_action
                    elif before_action:
                        return before_action
                    else:
                        return ""
            
            lines = text.split('\n')
            cleaned_lines = []
            skip_next = False
            for line in lines:
                if 'ROBOT_ACTION:' in line:
                    skip_next = True
                    continue
                if skip_next and line.strip() == '':
                    continue
                skip_next = False
                cleaned_lines.append(line)
            return '\n'.join(cleaned_lines).strip()
        
        return text
    
    def _get_next_question_instruction(self) -> str:
        """Determine which question type to use next for variety"""
        total = sum(self.question_types_used.values())
        if total < 3:
            return None
        
        least_used = min(self.question_types_used.items(), key=lambda x: x[1])
        
        instructions = {
            'open': "Ask an open-ended 'what' or 'how' question that requires elaboration.",
            'closed': "Ask a yes/no question to check comprehension.",
            'choice': "Give the child 2-3 choices to help them respond.",
            'descriptive': "Ask them to describe or explain something in detail."
        }
        
        return instructions.get(least_used[0])
    
    def _track_question_type(self, response: str):
        """Simple heuristic to track question variety"""
        lower = response.lower()
        
        if any(word in lower for word in ['what', 'how', 'why', 'tell me']):
            self.question_types_used['open'] += 1
        elif ' or ' in lower and '?' in response:
            self.question_types_used['choice'] += 1
        elif any(word in lower for word in ['describe', 'explain', 'what does', 'look like']):
            self.question_types_used['descriptive'] += 1
        elif '?' in response:
            self.question_types_used['closed'] += 1