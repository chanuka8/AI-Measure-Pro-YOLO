"""
state_manager.py - Persistent State Management
Saves and loads app state between sessions
"""

import json
import os
from datetime import datetime


class StateManager:
    def __init__(self, state_file="app_state.json"):
        self.state_file = state_file
        self.state = self.load_state()
    
    def load_state(self):
        """Load saved state from file"""
        default_state = {
            "version": "5.1",
            "voice_enabled": True,
            "last_units": "cm",
            "last_camera_id": 0,
            "last_model_path": "models/yolov8n.pt",
            "confidence_threshold": 0.40,
            "window_geometry": "1440x860",
            "window_position": None,
            "last_export_folder": "exports",
            "auto_save_enabled": False,
            "last_calibration_ppc": None,
            "last_used_features": {
                "barcode": True,
                "tracking": True,
                "voice": True,
                "tapmap": False
            },
            "user_preferences": {
                "show_measurement_lines": True,
                "show_accuracy_bar": True,
                "animation_speed": 15,
                "theme": "dark"
            },
            "session_history": [],
            "total_sessions": 0,
            "last_session": None,
            "first_run": True
        }
        
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    saved_state = json.load(f)
                    for key, value in default_state.items():
                        if key not in saved_state:
                            saved_state[key] = value
                    return saved_state
            except Exception as e:
                print(f"Error loading state: {e}")
                return default_state
        return default_state
    
    def save_state(self):
        """Save current state to file"""
        try:
            self.state["last_saved"] = datetime.now().isoformat()
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False
    
    def get(self, key, default=None):
        return self.state.get(key, default)
    
    def set(self, key, value):
        self.state[key] = value
        self.save_state()
    
    def update(self, updates_dict):
        self.state.update(updates_dict)
        self.save_state()
    
    def get_user_preference(self, key, default=None):
        return self.state.get("user_preferences", {}).get(key, default)
    
    def set_user_preference(self, key, value):
        if "user_preferences" not in self.state:
            self.state["user_preferences"] = {}
        self.state["user_preferences"][key] = value
        self.save_state()
    
    def increment_session_count(self):
        self.state["total_sessions"] = self.state.get("total_sessions", 0) + 1
        self.save_state()
        return self.state["total_sessions"]
    
    def mark_first_run_complete(self):
        if self.state.get("first_run", True):
            self.state["first_run"] = False
            self.save_state()
    
    def clear_state(self):
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.state = self.load_state()
        self.save_state()
        return True