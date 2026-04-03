"""
auth_manager.py - User Authentication & Session Management
Cybersecurity feature for AI Measure Pro (No external dependencies)
"""

import hashlib
import secrets
import time
from datetime import datetime
import json
import os


class AuthManager:
    def __init__(self, users_file="users.json", max_attempts=3, lockout_time=300):
        self.users_file = users_file
        self.max_attempts = max_attempts
        self.lockout_time = lockout_time
        self.current_user = None
        self.session_start = None
        self.failed_attempts = {}
        self.load_users()
    
    def load_users(self):
        """Load users from JSON file"""
        default_users = {
            "admin": {
                "password_hash": self._hash_password("Admin@2024"),
                "role": "admin",
                "created": datetime.now().isoformat()
            },
            "operator": {
                "password_hash": self._hash_password("Oper@2024"),
                "role": "operator",
                "created": datetime.now().isoformat()
            },
            "viewer": {
                "password_hash": self._hash_password("View@2024"),
                "role": "viewer",
                "created": datetime.now().isoformat()
            }
        }
        
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    self.users = json.load(f)
            except:
                self.users = default_users
        else:
            self.users = default_users
            self.save_users()
    
    def save_users(self):
        """Save users to file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def _hash_password(self, password):
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_obj.hex()}"
    
    def _verify_password(self, password, stored_hash):
        """Verify password against stored hash"""
        try:
            salt, hash_value = stored_hash.split(':')
            test_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return test_hash.hex() == hash_value
        except:
            return False
    
    def authenticate(self, username, password):
        """Authenticate user with brute force protection"""
        # Check lockout
        if username in self.failed_attempts:
            attempts, lockout_until = self.failed_attempts[username]
            if time.time() < lockout_until:
                remaining = int(lockout_until - time.time())
                return False, f"Account locked. Try after {remaining} seconds"
        
        if username not in self.users:
            return False, "Invalid credentials"
        
        if self._verify_password(password, self.users[username]["password_hash"]):
            # Successful login
            self.current_user = username
            self.session_start = time.time()
            self.failed_attempts.pop(username, None)
            return True, f"Welcome {username} ({self.users[username]['role']})"
        else:
            # Failed login
            if username not in self.failed_attempts:
                self.failed_attempts[username] = [1, time.time() + self.lockout_time]
            else:
                attempts, _ = self.failed_attempts[username]
                self.failed_attempts[username] = [attempts + 1, time.time() + self.lockout_time]
            remaining = self.max_attempts - self.failed_attempts[username][0]
            return False, f"Invalid credentials. {remaining} attempts left"
    
    def logout(self):
        """Logout current user"""
        self.current_user = None
        self.session_start = None
    
    def get_role(self):
        """Get current user's role"""
        if self.current_user:
            return self.users[self.current_user]["role"]
        return None
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.current_user is not None
    
    def get_current_user(self):
        """Get current username"""
        return self.current_user
    
    def session_timeout_check(self, timeout_seconds=1800):
        """Check if session has timed out (30 min default)"""
        if self.session_start and (time.time() - self.session_start) > timeout_seconds:
            self.logout()
            return True
        return False
    
    def change_password(self, username, old_password, new_password):
        """Change user password"""
        if username not in self.users:
            return False, "User not found"
        
        if not self._verify_password(old_password, self.users[username]["password_hash"]):
            return False, "Current password incorrect"
        
        self.users[username]["password_hash"] = self._hash_password(new_password)
        self.save_users()
        return True, "Password changed successfully"
    
    def add_user(self, username, password, role="viewer"):
        """Add new user (admin only)"""
        if username in self.users:
            return False, "User already exists"
        
        if role not in ["admin", "operator", "viewer"]:
            return False, "Invalid role"
        
        self.users[username] = {
            "password_hash": self._hash_password(password),
            "role": role,
            "created": datetime.now().isoformat()
        }
        self.save_users()
        return True, f"User {username} added with {role} role"
    
    def delete_user(self, username):
        """Delete user (admin only)"""
        if username == "admin":
            return False, "Cannot delete admin user"
        
        if username not in self.users:
            return False, "User not found"
        
        del self.users[username]
        self.save_users()
        return True, f"User {username} deleted"
    
    def list_users(self):
        """List all users (admin only)"""
        users_list = []
        for username, data in self.users.items():
            users_list.append({
                "username": username,
                "role": data["role"],
                "created": data.get("created", "Unknown")
            })
        return users_list