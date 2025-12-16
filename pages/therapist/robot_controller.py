"""
WaveGo Robot Controller
Sends action commands to WaveGo robot based on LLM decisions
Updated to include extended actions from ServoCtrl.h
"""

import requests
import agent_settings
from typing import Optional, Dict
import time


class RobotController:
    """Interface to control WaveGo robot actions"""
    
    # Available robot actions mapped to funcMode values
    # Based on ServoCtrl.h and WebPage.h
    ROBOT_ACTIONS = {
        'steady': 1,        # Balance/steady mode
        'stay_low': 2,      # Crouch down
        'handshake': 3,     # Handshake gesture
        'jump': 4,          # Jump action
        'bow': 5,           # Bow greeting
        'twist': 6,         # Twist/dance move
        'wave': 7,          # Wave (Previously Gimbal)
        'sit': 8,          # Sitting position
        'push_up': 9,      # Push-up exercise
        'jump_forward': 10, # Jump forward
        'jump_backward': 11,# Jump backward
        'dig': 12,          # Digging motion
        'sleep': 13,        # Sleep/rest mode
        'scared': 14        # Scared/shivering animation
    }
    
    def __init__(self):
        """
        Initialize robot controller
        
        Args:
            : IP address of WaveGo robot (from config if not provided)
            robot_port: Port number (default 80)
        """
        self.robot_ip = agent_settings.ROBOT_IP
        self.robot_port = agent_settings.ROBOT_PORT
        self.base_url = f"http://{self.robot_ip}:{self.robot_port}"
        self.last_action = None
        self.last_action_time = None
    
    def send_command(self, var: str, val: int, cmd: int = 0) -> bool:
        """
        Send control command to robot
        """
        try:
            url = f"{self.base_url}/control?var={var}&val={val}&cmd={cmd}"
            response = requests.get(url, timeout=2)
            
            if response.status_code == 200:
                print(f"✓ Robot command sent: {var}={val}")
                return True
            else:
                print(f"✗ Robot command failed: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"✗ Robot command timeout")
            return False
        except Exception as e:
            print(f"✗ Robot command error: {e}")
            return False
    
    def perform_action(self, action_name: str) -> bool:
        """
        Perform a named action
        """
        # Normalize input (e.g. "Jump Forward" -> "jump_forward")
        action_name = action_name.lower().replace(' ', '_')
        
        # Handle "digging" alias to "dig"
        if action_name == 'digging':
            action_name = 'dig'
        
        if action_name not in self.ROBOT_ACTIONS:
            print(f"✗ Unknown action: {action_name}")
            print(f"Available actions: {list(self.ROBOT_ACTIONS.keys())}")
            return False
        
        func_mode = self.ROBOT_ACTIONS[action_name]
        success = self.send_command('funcMode', func_mode, 0)
        
        if success:
            self.last_action = action_name
            self.last_action_time = time.time()
        
        return success
    
    def is_robot_available(self) -> bool:
        """Check if robot is reachable"""
        try:
            response = requests.get(self.base_url, timeout=2)
            return response.status_code == 200
        except:
            return False