import os
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, List, Tuple
from core.security_manager import SecurityManager, FileOperation, FilePermissions
from pathlib import Path
from dotenv import load_dotenv

class UserManager:
    VALID_ROLES = list(FilePermissions.ROLE_PERMISSIONS.keys())
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
        
        # Setup logging
        self._setup_logging()
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        
        self._ensure_root()
    
    def _setup_logging(self) -> None:
        """Setup user operations logging"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure logging
        self.logger = logging.getLogger('user_manager')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler(os.path.join(log_dir, "user_operations.log"))
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
    
    def _log_user_event(self, event_type: str, details: str, level: str = "INFO") -> None:
        """Log user management event"""
        log_method = getattr(self.logger, level.lower())
        log_method(f"{event_type}: {details}")
    
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
            self._log_user_event(
                "LOGIN_FAILED",
                f"Account locked for {email}. {remaining_minutes} minutes remaining",
                "WARNING"
            )
            raise ValueError(f"Account is locked. Try again in {remaining_minutes} minutes.")
        elif is_locked:
            self._log_user_event("LOGIN_FAILED", f"Account locked for {email}", "WARNING")
            raise ValueError("Account is locked. Please try again later.")

        users_data = self._load_users()
        
        if email not in users_data["users"]:
            self._record_failed_attempt(email)
            self._log_user_event("LOGIN_FAILED", f"Invalid email: {email}", "WARNING")
            return None
        
        user_data = users_data["users"][email]
        if not self.security_manager.verify_password(password, user_data["password_hash"].encode()):
            self._record_failed_attempt(email)
            self._log_user_event("LOGIN_FAILED", f"Invalid password for {email}", "WARNING")
            return None
        
        # Successful login - clear failed attempts
        if email in self.failed_attempts:
            del self.failed_attempts[email]
        
        # Update last login
        user_data["last_login"] = datetime.now(UTC).isoformat()
        users_data["users"][email] = user_data
        self._save_users(users_data)
        
        # Create session token
        token, expiry = self.security_manager.create_session_token({
            "email": email,
            "role": user_data["role"]
        })
        
        self._log_user_event(
            "LOGIN_SUCCESS", 
            f"User {email} logged in successfully. Session expires at {expiry.isoformat()}"
        )
        
        return token, user_data
    
    def _can_manage_role(self, admin_role: str, target_role: str) -> bool:
        """Check if admin_role can manage users with target_role"""
        admin_perms = FilePermissions.get_role_permissions(admin_role)
        target_perms = FilePermissions.get_role_permissions(target_role)
        
        # Root can manage all roles except other roots
        if admin_role == "root":
            return not FilePermissions.has_permission(target_role, FileOperation.SCHEMA_MODIFY)
        
        # Admin can manage roles with fewer permissions
        if admin_role == "admin":
            return (not FilePermissions.has_permission(target_role, FileOperation.SCHEMA_MODIFY) and
                   not FilePermissions.has_permission(target_role, FileOperation.DELETE))
        
        return False

    def create_user(self, admin_token: str, email: str, password: str, role: str = "user") -> bool:
        """Create new user (requires appropriate permissions)"""
        # Verify token and permissions
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or not FilePermissions.has_permission(token_data["role"], FileOperation.USER_CREATE):
            self._log_user_event(
                "USER_CREATE_FAILED",
                f"Insufficient permissions for {token_data['email'] if token_data else 'unknown'}",
                "ERROR"
            )
            return False
            
        # Get token role
        token_role = token_data["role"]
        admin_email = token_data["email"]
        
        # Validate role
        if role not in self.VALID_ROLES:
            self._log_user_event(
                "USER_CREATE_FAILED",
                f"Invalid role {role} specified by {admin_email}",
                "ERROR"
            )
            return False
            
        # Check if admin can manage this role
        if not FilePermissions.can_manage_role(token_role, role):
            self._log_user_event(
                "USER_CREATE_FAILED",
                f"Admin {admin_email} cannot create users with role {role}",
                "ERROR"
            )
            return False
        
        users_data = self._load_users()
        
        # Check if user already exists
        if email in users_data["users"]:
            self._log_user_event(
                "USER_CREATE_FAILED",
                f"User {email} already exists. Attempted by {admin_email}",
                "ERROR"
            )
            return False
        
        # Create new user
        users_data["users"][email] = {
            "password_hash": self.security_manager.hash_password(password).decode(),
            "role": role,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": admin_email,
            "last_login": None,
            "is_root": role == "root"
        }
        
        self._save_users(users_data)
        
        self._log_user_event(
            "USER_CREATED",
            f"New user {email} created with role {role} by {admin_email}"
        )
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
        """Reset user password (requires appropriate permissions)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or not FilePermissions.has_permission(token_data["role"], FileOperation.PASSWORD_RESET):
            return False
            
        token_role = token_data["role"]
        users_data = self._load_users()
        
        if user_email not in users_data["users"]:
            return False
            
        target_user = users_data["users"][user_email]
        
        # Check if admin can manage this user's role
        if not FilePermissions.can_manage_role(token_role, target_user["role"]):
            return False
        
        # Update password
        target_user["password_hash"] = self.security_manager.hash_password(new_password).decode()
        target_user["password_reset_by"] = token_data["email"]
        target_user["password_reset_at"] = datetime.now(UTC).isoformat()
        
        users_data["users"][user_email] = target_user
        self._save_users(users_data)
        
        return True
    
    def get_users(self, admin_token: str) -> Optional[List[Dict]]:
        """Get list of users (requires view permission)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or not FilePermissions.has_permission(token_data["role"], FileOperation.USER_VIEW):
            return None
            
        users_data = self._load_users()
        token_role = token_data["role"]
        
        return [
            {
                "email": email,
                "role": data["role"],
                "created_at": data["created_at"],
                "last_login": data["last_login"],
                "can_modify": FilePermissions.can_manage_role(token_role, data["role"]),
                "can_delete": (FilePermissions.has_permission(token_role, FileOperation.USER_DELETE) and 
                             FilePermissions.can_manage_role(token_role, data["role"]) and
                             not data.get("is_root", False))
            }
            for email, data in users_data["users"].items()
        ]
    
    def delete_user(self, admin_token: str, user_email: str) -> bool:
        """Delete user (requires appropriate permissions)"""
        try:
            # Verify token and permissions
            token_data = self.security_manager.verify_session_token(admin_token)
            if not token_data or not FilePermissions.has_permission(token_data["role"], FileOperation.USER_DELETE):
                self._log_user_event(
                    "USER_DELETE_FAILED",
                    f"Insufficient permissions for {token_data['email'] if token_data else 'unknown'}",
                    "ERROR"
                )
                return False
                
            token_role = token_data["role"]
            admin_email = token_data["email"]
            
            users_data = self._load_users()
            
            # Check if user exists
            if user_email not in users_data["users"]:
                self._log_user_event(
                    "USER_DELETE_FAILED",
                    f"User {user_email} not found. Attempted by {admin_email}",
                    "ERROR"
                )
                return False
                
            target_user = users_data["users"][user_email]
            target_role = target_user["role"]
            
            # Check if admin can manage this user's role
            if not FilePermissions.can_manage_role(token_role, target_role):
                self._log_user_event(
                    "USER_DELETE_FAILED",
                    f"Admin {admin_email} cannot delete users with role {target_role}",
                    "ERROR"
                )
                return False
            
            # Cannot delete root user
            if target_user.get("is_root", False):
                self._log_user_event(
                    "USER_DELETE_FAILED",
                    f"Cannot delete root user {user_email}. Attempted by {admin_email}",
                    "ERROR"
                )
                return False
            
            # Delete user
            del users_data["users"][user_email]
            self._save_users(users_data)
            
            self._log_user_event(
                "USER_DELETED",
                f"User {user_email} deleted by {admin_email}"
            )
            return True
                
        except Exception as e:
            self._log_user_event(
                "USER_DELETE_ERROR",
                f"Error deleting user {user_email}: {str(e)}",
                "ERROR"
            )
            return False

    def change_user_role(self, admin_token: str, user_email: str, new_role: str) -> bool:
        """Change user role (requires appropriate permissions)"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data or not FilePermissions.has_permission(token_data["role"], FileOperation.USER_MODIFY):
            self._log_user_event(
                "ROLE_CHANGE_FAILED",
                f"Insufficient permissions for {token_data['email'] if token_data else 'unknown'}",
                "ERROR"
            )
            return False
            
        token_role = token_data["role"]
        admin_email = token_data["email"]
        
        # Validate new role
        if new_role not in self.VALID_ROLES:
            self._log_user_event(
                "ROLE_CHANGE_FAILED",
                f"Invalid role {new_role} specified by {admin_email}",
                "ERROR"
            )
            return False
            
        users_data = self._load_users()
        if user_email not in users_data["users"]:
            self._log_user_event(
                "ROLE_CHANGE_FAILED",
                f"User {user_email} not found. Attempted by {admin_email}",
                "ERROR"
            )
            return False
            
        target_user = users_data["users"][user_email]
        current_role = target_user["role"]
        
        # Check if admin can manage both current and new roles
        if not (FilePermissions.can_manage_role(token_role, current_role) and 
                FilePermissions.can_manage_role(token_role, new_role)):
            self._log_user_event(
                "ROLE_CHANGE_FAILED",
                f"Admin {admin_email} cannot change role from {current_role} to {new_role}",
                "ERROR"
            )
            return False
        
        # Cannot modify root user
        if target_user.get("is_root", False):
            self._log_user_event(
                "ROLE_CHANGE_FAILED",
                f"Cannot modify root user {user_email}. Attempted by {admin_email}",
                "ERROR"
            )
            return False
        
        # Update role
        target_user["role"] = new_role
        target_user["modified_at"] = datetime.now(UTC).isoformat()
        target_user["modified_by"] = admin_email
        
        users_data["users"][user_email] = target_user
        self._save_users(users_data)
        
        self._log_user_event(
            "ROLE_CHANGED",
            f"User {user_email} role changed from {current_role} to {new_role} by {admin_email}"
        )
        return True

    def get_manageable_roles(self, admin_token: str) -> List[str]:
        """Get list of roles that can be managed by the token holder"""
        token_data = self.security_manager.verify_session_token(admin_token)
        if not token_data:
            return []
        
        return FilePermissions.get_manageable_roles(token_data["role"]) 