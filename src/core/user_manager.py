import os
import json
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, List, Tuple
from core.security_manager import SecurityManager
from pathlib import Path
from dotenv import load_dotenv

class UserManager:
    VALID_ROLES = ["root", "admin", "moderator", "user"]  # Added root role
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
        
        self._ensure_root()
    
    def _get_required_env(self, var_name: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(var_name)
        if value is None:
            raise ValueError(f"Required environment variable {var_name} is not set. Please check your .env file.")
        return value
    
    def _ensure_root(self) -> None:
        """Ensure root user exists"""
        try:
            if not os.path.exists(self.users_file):
                # Get required root credentials from environment
                root_email = self._get_required_env("ROOT_EMAIL")
                root_password = self._get_required_env("ROOT_PASSWORD")
                
                # Create root user
                root_data = {
                    "users": {
                        root_email: {
                            "password_hash": self.security_manager.hash_password(root_password).decode(),
                            "role": "root",
                            "created_at": datetime.now(UTC).isoformat(),
                            "last_login": None,
                            "is_root": True
                        }
                    }
                }
                
                # Encrypt and save
                encrypted_data = self.security_manager.encrypt_file(root_data, self.master_password)
                with open(self.users_file, 'wb') as f:
                    f.write(encrypted_data)
                
                # Verify the data was written correctly
                with open(self.users_file, 'rb') as f:
                    test_data = f.read()
                decrypted_data = self.security_manager.decrypt_file(test_data, self.master_password)
                if decrypted_data != root_data:
                    raise ValueError("Root data verification failed")
                    
        except Exception as e:
            raise ValueError(f"Failed to create root account: {str(e)}")
    
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
        now = datetime.now(UTC)
        
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
        now = datetime.now(UTC)
        if email not in self.failed_attempts:
            self.failed_attempts[email] = []
        self.failed_attempts[email].append(now)

    def authenticate_user(self, email: str, password: str) -> Optional[Tuple[str, dict]]:
        """Authenticate user and return session token if successful"""
        # Check for account lockout
        is_locked, lockout_end = self._check_account_lockout(email)
        if is_locked and lockout_end:
            remaining_minutes = int((lockout_end - datetime.now(UTC)).total_seconds() / 60)
            raise ValueError(f"Account is locked. Try again in {remaining_minutes} minutes.")
        elif is_locked:
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
        user_data["last_login"] = datetime.now(UTC).isoformat()
        users_data["users"][email] = user_data
        self._save_users(users_data)
        
        # Create session token
        token, _ = self.security_manager.create_session_token({
            "email": email,
            "role": user_data["role"]
        })
        
        return token, user_data
    
    def create_user(self, admin_token: str, email: str, password: str, role: str = "user") -> bool:
        """Create new user (requires admin/root token)"""
        # Verify admin/root token
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data:
            return False
            
        # Get token role
        token_role = token_data["role"]
        
        # Validate role hierarchy
        if role not in self.VALID_ROLES:
            return False
            
        # Root can create any role
        if token_role == "root":
            pass
        # Admin can only create moderator and user roles
        elif token_role == "admin":
            if role in ["root", "admin"]:
                return False
        else:
            return False
        
        users_data = self._load_users()
        
        # Check if user already exists
        if email in users_data["users"]:
            return False
        
        # Create new user
        users_data["users"][email] = {
            "password_hash": self.security_manager.hash_password(password).decode(),
            "role": role,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": token_data["email"],
            "last_login": None,
            "is_root": role == "root"
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
        """Reset user password (requires admin/root token)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data:
            return False
            
        token_role = token_data["role"]
        
        users_data = self._load_users()
        if user_email not in users_data["users"]:
            return False
            
        target_user = users_data["users"][user_email]
        
        # Root can reset any password
        if token_role == "root":
            pass
        # Admin can only reset moderator and user passwords
        elif token_role == "admin":
            if target_user["role"] in ["root", "admin"]:
                return False
        else:
            return False
        
        # Update password
        target_user["password_hash"] = self.security_manager.hash_password(new_password).decode()
        users_data["users"][user_email] = target_user
        self._save_users(users_data)
        
        return True
    
    def get_users(self, admin_token: str) -> Optional[List[Dict]]:
        """Get list of users (requires admin/root token)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or token_data["role"] not in ["admin", "root"]:
            return None
            
        users_data = self._load_users()
        
        # If admin, filter out root and admin users
        if token_data["role"] == "admin":
            return [
                {
                    "email": email,
                    "role": data["role"],
                    "created_at": data["created_at"],
                    "last_login": data["last_login"]
                }
                for email, data in users_data["users"].items()
                if data["role"] not in ["root", "admin"]
            ]
        
        # If root, show all users
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
        """Delete user (requires admin/root token)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data:
            return False
            
        token_role = token_data["role"]
        
        users_data = self._load_users()
        if user_email not in users_data["users"]:
            return False
            
        target_user = users_data["users"][user_email]
        
        # Cannot delete root user
        if target_user.get("is_root", False):
            return False
            
        # Root can delete any non-root user
        if token_role == "root":
            pass
        # Admin can only delete moderator and user accounts
        elif token_role == "admin":
            if target_user["role"] in ["root", "admin"]:
                return False
        else:
            return False
        
        del users_data["users"][user_email]
        self._save_users(users_data)
        
        return True 