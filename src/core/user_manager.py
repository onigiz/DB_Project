import os
import json
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from .security_manager import SecurityManager

class UserManager:
    VALID_ROLES = ["admin", "moderator", "user"]  # Added moderator role
    
    def __init__(self, security_manager: SecurityManager, users_file: str = "users.enc"):
        """Initialize UserManager with SecurityManager instance"""
        self.security_manager = security_manager
        self.users_file = users_file
        self.master_password = os.getenv("MASTER_PASSWORD", "default_master_password")
        self._ensure_admin()
    
    def _ensure_admin(self) -> None:
        """Ensure admin user exists"""
        if not os.path.exists(self.users_file):
            # Create default admin user
            admin_data = {
                "users": {
                    "admin@company.com": {
                        "password_hash": self.security_manager.hash_password("admin123").decode(),
                        "role": "admin",
                        "created_at": datetime.utcnow().isoformat(),
                        "last_login": None
                    }
                }
            }
            # Encrypt and save
            encrypted_data = self.security_manager.encrypt_file(admin_data, self.master_password)
            with open(self.users_file, 'wb') as f:
                f.write(encrypted_data)
    
    def _load_users(self) -> dict:
        """Load users data from encrypted file"""
        try:
            with open(self.users_file, 'rb') as f:
                encrypted_data = f.read()
            return self.security_manager.decrypt_file(encrypted_data, self.master_password)
        except FileNotFoundError:
            return {"users": {}}
    
    def _save_users(self, users_data: dict) -> None:
        """Save users data to encrypted file"""
        encrypted_data = self.security_manager.encrypt_file(users_data, self.master_password)
        with open(self.users_file, 'wb') as f:
            f.write(encrypted_data)
    
    def authenticate_user(self, email: str, password: str) -> Optional[Tuple[str, dict]]:
        """Authenticate user and return session token if successful"""
        users_data = self._load_users()
        
        if email not in users_data["users"]:
            return None
        
        user_data = users_data["users"][email]
        if not self.security_manager.verify_password(password, user_data["password_hash"].encode()):
            return None
        
        # Update last login
        user_data["last_login"] = datetime.utcnow().isoformat()
        users_data["users"][email] = user_data
        self._save_users(users_data)
        
        # Create session token
        token, _ = self.security_manager.create_session_token({
            "email": email,
            "role": user_data["role"]
        })
        
        return token, user_data
    
    def create_user(self, admin_token: str, email: str, password: str, role: str = "user") -> bool:
        """Create new user (requires admin token)"""
        # Verify admin token
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or token_data["role"] != "admin":
            return False
        
        # Validate role
        if role not in self.VALID_ROLES:
            return False
        
        users_data = self._load_users()
        
        # Check if user already exists
        if email in users_data["users"]:
            return False
        
        # Create new user
        users_data["users"][email] = {
            "password_hash": self.security_manager.hash_password(password).decode(),
            "role": role,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": token_data["email"],
            "last_login": None
        }
        
        self._save_users(users_data)
        return True
    
    def change_password(self, token: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        token_data = self.security_manager.verify_session_token(token)
        if not token_data:
            return False
        
        email = token_data["email"]
        users_data = self._load_users()
        
        if email not in users_data["users"]:
            return False
        
        user_data = users_data["users"][email]
        if not self.security_manager.verify_password(old_password, user_data["password_hash"].encode()):
            return False
        
        # Update password
        user_data["password_hash"] = self.security_manager.hash_password(new_password).decode()
        users_data["users"][email] = user_data
        self._save_users(users_data)
        
        return True
    
    def reset_password(self, admin_token: str, user_email: str, new_password: str) -> bool:
        """Reset user password (requires admin token)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or token_data["role"] != "admin":
            return False
        
        users_data = self._load_users()
        if user_email not in users_data["users"]:
            return False
        
        # Update password
        user_data = users_data["users"][user_email]
        user_data["password_hash"] = self.security_manager.hash_password(new_password).decode()
        users_data["users"][user_email] = user_data
        self._save_users(users_data)
        
        return True
    
    def get_users(self, admin_token: str) -> Optional[List[Dict]]:
        """Get list of users (requires admin token)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or token_data["role"] != "admin":
            return None
        
        users_data = self._load_users()
        return [
            {
                "email": email,
                "role": data["role"],
                "created_at": data["created_at"],
                "last_login": data["last_login"]
            }
            for email, data in users_data["users"].items()
        ]
    
    def delete_user(self, admin_token: str, user_email: str) -> bool:
        """Delete user (requires admin token)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or token_data["role"] != "admin":
            return False
        
        users_data = self._load_users()
        if user_email not in users_data["users"]:
            return False
        
        # Cannot delete last admin
        if users_data["users"][user_email]["role"] == "admin":
            admin_count = sum(1 for u in users_data["users"].values() if u["role"] == "admin")
            if admin_count <= 1:
                return False
        
        del users_data["users"][user_email]
        self._save_users(users_data)
        
        return True 