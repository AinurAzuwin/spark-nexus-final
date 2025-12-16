"""
Picture Handler for Language Screening
Manages picture prompts for eliciting descriptive language
"""

import os
import random
from typing import Dict, List, Optional
import base64

class PictureHandler:
    """Manages picture prompts for language elicitation"""
    
    def __init__(self, pictures_dir: str = "picture_prompts"):
        """
        Initialize picture handler
        
        Args:
            pictures_dir: Directory containing picture prompt images
        """
        self.pictures_dir = pictures_dir
        self.available_pictures = []
        self.pictures_shown = []
        self.current_picture = None
        
        # Picture metadata for clinical targeting
        self.picture_metadata = {
            'boy_with_dog.jpg': {
                'complexity': 'medium',
                'targets': ['subject-verb agreement', 'prepositions', 'descriptive adjectives'],
                'themes': ['animals', 'relationships', 'actions']
            },
            
            'toys_on_floor.jpg': {
                'complexity': 'low',
                'targets': ['basic nouns', 'colors', 'counting', 'spatial terms'],
                'themes': ['toys', 'play', 'objects']
            },
            'playground_scene.jpg': {
                'complexity': 'medium',
                'targets': ['action verbs', 'social language', 'emotions'],
                'themes': ['play', 'friends', 'movement']
            }
        }
        
        # Load available pictures
        self._load_pictures()
        # Create test pictures if none exist
        if not self.available_pictures:
            self.create_test_pictures()
    
    def _load_pictures(self):
        """Load available pictures from directory"""
        if not os.path.exists(self.pictures_dir):
            print(f"⚠️ Pictures directory not found: {self.pictures_dir}")
            print(f"   Creating directory...")
            os.makedirs(self.pictures_dir, exist_ok=True)
            return
        
        # Get all image files
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        for filename in os.listdir(self.pictures_dir):
            if any(filename.lower().endswith(ext) for ext in valid_extensions):
                self.available_pictures.append(filename)
        
        print(f"Loaded {len(self.available_pictures)} picture prompts")
        for pic in self.available_pictures:
            metadata = self.picture_metadata.get(pic, {'complexity': 'unknown'})
            print(f"   - {pic} (complexity: {metadata.get('complexity')})")
    
    def should_show_picture(self, conversation_turn: int, child_responses: List[str]) -> bool:
        """
        Decide if it's a good time to show a picture
        
        Args:
            conversation_turn: Current turn number in conversation
            child_responses: List of child's previous responses
            
        Returns:
            True if picture should be shown
        """
        # Don't show if we've already shown all pictures
        if len(self.pictures_shown) >= len(self.available_pictures):
            print(f"📸 All {len(self.available_pictures)} pictures already shown")
            return False
        
        # AGGRESSIVE: Show first picture after turn 3
        if conversation_turn == 4 and len(self.pictures_shown) == 0:
            print(f"📸 Triggering FIRST picture at turn {conversation_turn}")
            return True
        
        # Show picture every 6-8 turns after first one
        pictures_shown_count = len(self.pictures_shown)
        if pictures_shown_count > 0:
            last_picture_turn = 4 + ((pictures_shown_count - 1) * 7)
            next_picture_turn = last_picture_turn + random.randint(6, 8)
            
            if conversation_turn >= next_picture_turn:
                print(f"📸 Triggering picture #{pictures_shown_count + 1} at turn {conversation_turn}")
                return True
        
        # Show picture if child seems to be struggling (very short responses)
        if len(child_responses) >= 3:
            recent_responses = child_responses[-3:]
            avg_length = sum(len(r.split()) for r in recent_responses) / len(recent_responses)
            if avg_length < 3:  # Very short responses
                print(f"📸 Triggering picture due to short responses (avg: {avg_length:.1f} words)")
                return True
        
        return False
    
    def select_picture(self, child_age: Optional[int] = None) -> Optional[Dict]:
        """
        Select an appropriate picture that hasn't been shown yet
        
        Args:
            child_age: Child's age for complexity matching
            
        Returns:
            Dict with picture info or None if no pictures available
        """
        # Get pictures not yet shown
        remaining_pictures = [p for p in self.available_pictures if p not in self.pictures_shown]
        
        if not remaining_pictures:
            print("⚠️ No more pictures available")
            return None
        
        # Filter by complexity if age is known
        if child_age:
            if child_age <= 4:
                preferred_complexity = 'low'
            elif child_age == 5:
                preferred_complexity = 'medium'
            else:
                preferred_complexity = 'high'
            
            # Try to get picture with preferred complexity
            suitable_pictures = [
                p for p in remaining_pictures 
                if self.picture_metadata.get(p, {}).get('complexity') == preferred_complexity
            ]
            
            if suitable_pictures:
                selected = random.choice(suitable_pictures)
            else:
                selected = random.choice(remaining_pictures)
        else:
            selected = random.choice(remaining_pictures)
        
        # Mark as shown
        self.pictures_shown.append(selected)
        self.current_picture = selected
        
        # Get metadata
        metadata = self.picture_metadata.get(selected, {
            'complexity': 'unknown',
            'targets': [],
            'themes': []
        })
        
        # Get file path
        filepath = os.path.join(self.pictures_dir, selected)
        
        print(f"🖼️ Selected picture: {selected}")
        print(f"   Complexity: {metadata.get('complexity')}")
        print(f"   Targets: {', '.join(metadata.get('targets', []))}")
        
        return {
            'filename': selected,
            'filepath': filepath,
            'complexity': metadata.get('complexity'),
            'targets': metadata.get('targets', []),
            'themes': metadata.get('themes', []),
            'metadata': metadata
        }
    
    def get_picture_base64(self, filepath: str) -> Optional[str]:
        """
        Convert picture to base64 for display
        
        Args:
            filepath: Path to picture file
            
        Returns:
            Base64 encoded string or None
        """
        try:
            with open(filepath, 'rb') as f:
                image_bytes = f.read()
                base64_str = base64.b64encode(image_bytes).decode('utf-8')
                return base64_str
        except Exception as e:
            print(f"❌ Error encoding picture: {e}")
            return None
    
    def get_picture_prompt(self, picture_info: Dict) -> str:
        """
        Generate appropriate prompt for the picture
        
        Args:
            picture_info: Picture information dict
            
        Returns:
            Prompt text for the agent
        """
        prompts = [
            "Look at this picture! What do you see?",
            "I have something fun to show you! Can you tell me what's in this picture?",
            "Let's look at this picture together. What do you see happening?",
            "Check this out! What can you tell me about this picture?",
            "I want to show you something! What's going on in this picture?"
        ]
        
        return random.choice(prompts)
    
    def get_followup_prompts(self) -> List[str]:
        """
        Get follow-up prompts to elicit more description
        
        Returns:
            List of follow-up prompts
        """
        return [
            "What else do you see?",
            "Can you tell me more about that?",
            "What is the [person/animal] doing?",
            "What colors do you see?",
            "How do you think they feel?",
            "What might happen next?",
            "Can you describe the [object]?"
        ]
    
    def reset(self):
        """Reset for new session"""
        self.pictures_shown = []
        self.current_picture = None
        print("🔄 Picture handler reset for new session")

    def create_test_pictures(self):
        """Create test picture files if none exist"""
        if not self.available_pictures:
            print("⚠️ No pictures found. Creating test placeholders...")
            
            test_pictures = [
                'boy_with_dog.jpg',
                'toys_on_floor.jpg', 
                'playground_scene.jpg'
            ]
            
            for pic in test_pictures:
                filepath = os.path.join(self.pictures_dir, pic)
                if not os.path.exists(filepath):
                    # Create a simple placeholder (1x1 pixel base64)
                    with open(filepath, 'w') as f:
                        f.write("PLACEHOLDER_PICTURE")
                    print(f"   Created placeholder: {pic}")
            
            self._load_pictures()