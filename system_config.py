"""
Configuration manager that handles environment detection
"""
import os
import subprocess
import sys
import time
import requests

class AppConfig:
    # Detect environment
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    
    # Development settings
    DEV_CHILD_PORT = 8502
    DEV_MAIN_PORT = 8501
    
    # Production settings (will use query parameters)
    PROD_USE_QUERY_PARAMS = True
    
    # Process tracking
    child_process = None
    
    @classmethod
    def is_production(cls):
        """Check if running in production mode"""
        return cls.ENVIRONMENT == 'production' or os.environ.get('STREAMLIT_SHARING') == 'true'
    
    @classmethod
    def get_child_url(cls):
        """Get the correct child interface URL"""
        if cls.is_production():
            # Production: same domain, query parameter
            return "?mode=child"  # Relative URL
        else:
            # Development: separate port
            return f"http://localhost:{cls.DEV_CHILD_PORT}"
    
    @classmethod
    def is_child_running(cls):
        """Check if child view process is running"""
        try:
            response = requests.get(f"http://localhost:{cls.DEV_CHILD_PORT}", timeout=1)
            return response.status_code == 200
        except:
            return False
    
    @classmethod
    def start_child_view(cls):
        """Start child_view.py in background (only in development)"""
        if cls.is_production():
            print("🌐 Production mode: Child view runs in same process")
            return None
        
        if cls.is_child_running():
            print("✅ Child view already running on port", cls.DEV_CHILD_PORT)
            return None
        
        print(f"🚀 Starting child view on port {cls.DEV_CHILD_PORT}...")
        
        try:
            # 1. Define Paths
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")) # Adjust "../.." based on where system_config.py is
            # TRICK: Since system_config.py is usually in root or close to it, let's just use os.getcwd() if you run the main app from root.
            # BETTER WAY:
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            # If system_config.py is in the root folder:
            project_root = current_file_dir 

            # 2. Path to child view
            child_path = os.path.join(project_root, "pages", "therapist", "child_view.py")

            # 2. PREPARE ENVIRONMENT
            # Force Python to use UTF-8 for IO (Fixes the emoji encoding crash)
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["LC_ALL"] = "en_US.UTF-8"
            env["LANG"] = "en_US.UTF-8"

            # 3. SETUP LOGGING
            # Instead of PIPE, write to a file we can read
            log_file = open("child_debug.log", "w", encoding="utf-8")

            # 3. The FIX: Pass cwd=project_root
            process = subprocess.Popen(
                [
                    sys.executable, "-m", "streamlit", "run",
                    child_path,
                    "--server.port", str(cls.DEV_CHILD_PORT),
                    "--server.headless", "true",
                    "--browser.gatherUsageStats", "false"
                ],
                cwd=project_root,  # <--- THIS IS THE CRITICAL FIX FOR THE DB/BUTTON
                env=env,
                stdout=log_file,
                stderr=log_file,
                start_new_session=True
            )
            
            cls.child_process = process
            
            # Wait for it to start
            for i in range(15): # Increased wait time slightly
                time.sleep(1)
                if cls.is_child_running():
                    print(f"✅ Child view started successfully on port {cls.DEV_CHILD_PORT}")
                    return process
            
            print("⚠️ Child view started but not responding yet... Check child_debug.log for errors")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start child view: {e}")
            return None
    
    @classmethod
    def stop_child_view(cls):
        """Stop child view process"""
        if cls.child_process:
            try:
                cls.child_process.terminate()
                cls.child_process.wait(timeout=5)
                print("🛑 Child view stopped")
            except:
                cls.child_process.kill()
                print("🛑 Child view force killed")
            finally:
                cls.child_process = None
