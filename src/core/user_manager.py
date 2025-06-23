import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from core.security_manager import SecurityManager
from pathlib import Path
from dotenv import load_dotenv

class UserManager:
    VALID_ROLES = ["admin", "moderator", "user"]  # Added moderator role
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 15  # minutes
    
    def __init__(self, security_manager: SecurityManager, users_file: Optional[str] = None):
        """Initialize UserManager with SecurityManager instance"""
        # Load environment variables
        load_dotenv()
        
        self.security_manager = security_manager
        
        # Get required environment variables
        self.users_file = users_file or self._get_required_env("USERS_FILE")
        self.master_password = self._get_required_env("MASTER_PASSWORD")
        
        # Failed login attempts tracking
        self.failed_attempts = {}  # {email: [timestamp, ...]}
        self.account_lockouts = {}  # {email: lockout_end_time}
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        
        self._ensure_admin()
    
    def _get_required_env(self, var_name: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(var_name)
        if value is None:
            raise ValueError(f"Required environment variable {var_name} is not set. Please check your .env file.")
        return value
    
    def _ensure_admin(self) -> None:
        """Ensure admin user exists"""
        try:
            if not os.path.exists(self.users_file):
                # Get required admin credentials from environment
                admin_email = self._get_required_env("ADMIN_EMAIL")
                admin_password = self._get_required_env("ADMIN_PASSWORD")
                
                # Create admin user
                admin_data = {
                    "users": {
                        admin_email: {
                            "password_hash": self.security_manager.hash_password(admin_password).decode(),
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
                
                # Verify the data was written correctly
                with open(self.users_file, 'rb') as f:
                    test_data = f.read()
                decrypted_data = self.security_manager.decrypt_file(test_data, self.master_password)
                if decrypted_data != admin_data:
                    raise ValueError("Admin data verification failed")
                    
        except Exception as e:
            raise ValueError(f"Failed to create admin account: {str(e)}")
    
    def _load_users(self) -> dict:
        """Load users data from encrypted file"""
        try:
            if not os.path.exists(self.users_file):
                return {"users": {}}
                
            with open(self.users_file, 'rb') as f:
                encrypted_data = f.read()
            return self.security_manager.decrypt_file(encrypted_data, self.master_password)
        except Exception as e:
            raise ValueError(f"Failed to load users data: {str(e)}")
    
    def _save_users(self, users_data: dict) -> None:
        """Save users data to encrypted file"""
        encrypted_data = self.security_manager.encrypt_file(users_data, self.master_password)
        with open(self.users_file, 'wb') as f:
            f.write(encrypted_data)
    
    def _check_account_lockout(self, email: str) -> Tuple[bool, Optional[datetime]]:
        """Check if account is locked out"""
        now = datetime.utcnow()
        
        # Clear old lockouts
        self.account_lockouts = {
            e: t for e, t in self.account_lockouts.items()
            if t > now
        }
        
        # Check if account is locked
        if email in self.account_lockouts:
            return True, self.account_lockouts[email]
        
        # Clear old failed attempts
        if email in self.failed_attempts:
            self.failed_attempts[email] = [
                attempt for attempt in self.failed_attempts[email]
                if (now - attempt).total_seconds() < self.LOCKOUT_DURATION * 60
            ]
            
            # Check if too many recent failed attempts
            if len(self.failed_attempts[email]) >= self.MAX_LOGIN_ATTEMPTS:
                lockout_end = now + timedelta(minutes=self.LOCKOUT_DURATION)
                self.account_lockouts[email] = lockout_end
                return True, lockout_end
        
        return False, None

    def _record_failed_attempt(self, email: str) -> None:
        """Record a failed login attempt"""
        now = datetime.utcnow()
        if email not in self.failed_attempts:
            self.failed_attempts[email] = []
        self.failed_attempts[email].append(now)

    def authenticate_user(self, email: str, password: str) -> Optional[Tuple[str, dict]]:
        """Authenticate user and return session token if successful"""
        # Check for account lockout
        is_locked, lockout_end = self._check_account_lockout(email)
        if is_locked and lockout_end:  # Add null check
            remaining_minutes = int((lockout_end - datetime.utcnow()).total_seconds() / 60)
            raise ValueError(f"Account is locked. Try again in {remaining_minutes} minutes.")
        elif is_locked:  # Handle case where lockout_end is None
            raise ValueError("Account is locked. Please try again later.")

        users_data = self._load_users()
        
        if email not in users_data["users"]:
            self._record_failed_attempt(email)
            return None
        
        user_data = users_data["users"][email]
        if not self.security_manager.verify_password(password, user_data["password_hash"].encode()):
            self._record_failed_attempt(email)
            return None
        
        # Successful login - clear failed attempts
        if email in self.failed_attempts:
            del self.failed_attempts[email]
        
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