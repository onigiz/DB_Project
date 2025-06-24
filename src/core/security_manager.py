import os
import json
import bcrypt
import re
import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, Tuple, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from base64 import b64encode, b64decode
from enum import Enum, auto

class FileOperation(Enum):
    READ = auto()
    WRITE = auto()
    DELETE = auto()
    SCHEMA_MODIFY = auto()
    # User management operations
    USER_CREATE = auto()
    USER_DELETE = auto()
    USER_MODIFY = auto()
    USER_VIEW = auto()
    PASSWORD_RESET = auto()

class FilePermissions:
    """Manages role-based file permissions"""
    
    ROLE_PERMISSIONS = {
        "root": {
            # File operations
            FileOperation.READ: True,
            FileOperation.WRITE: True,
            FileOperation.DELETE: True,
            FileOperation.SCHEMA_MODIFY: True,
            # User management
            FileOperation.USER_CREATE: True,
            FileOperation.USER_DELETE: True,
            FileOperation.USER_MODIFY: True,
            FileOperation.USER_VIEW: True,
            FileOperation.PASSWORD_RESET: True
        },
        "admin": {
            # File operations
            FileOperation.READ: True,
            FileOperation.WRITE: True,
            FileOperation.DELETE: True,
            FileOperation.SCHEMA_MODIFY: True,
            # User management - limited
            FileOperation.USER_CREATE: True,
            FileOperation.USER_DELETE: True,
            FileOperation.USER_MODIFY: True,
            FileOperation.USER_VIEW: True,
            FileOperation.PASSWORD_RESET: True
        },
        "moderator": {
            # File operations
            FileOperation.READ: True,
            FileOperation.WRITE: True,
            FileOperation.DELETE: False,
            FileOperation.SCHEMA_MODIFY: False,
            # User management - very limited
            FileOperation.USER_CREATE: False,
            FileOperation.USER_DELETE: False,
            FileOperation.USER_MODIFY: False,
            FileOperation.USER_VIEW: True,
            FileOperation.PASSWORD_RESET: False
        },
        "user": {
            # File operations
            FileOperation.READ: True,
            FileOperation.WRITE: False,
            FileOperation.DELETE: False,
            FileOperation.SCHEMA_MODIFY: False,
            # User management - none
            FileOperation.USER_CREATE: False,
            FileOperation.USER_DELETE: False,
            FileOperation.USER_MODIFY: False,
            FileOperation.USER_VIEW: False,
            FileOperation.PASSWORD_RESET: False
        }
    }

    # Role hierarchy definition
    ROLE_HIERARCHY = {
        "root": ["admin", "moderator", "user"],
        "admin": ["moderator", "user"],
        "moderator": ["user"],
        "user": []
    }

    @classmethod
    def has_permission(cls, role: str, operation: FileOperation) -> bool:
        """Check if role has permission for operation"""
        if role not in cls.ROLE_PERMISSIONS:
            return False
        return cls.ROLE_PERMISSIONS[role].get(operation, False)

    @classmethod
    def get_role_permissions(cls, role: str) -> Dict:
        """Get all permissions for a role"""
        return cls.ROLE_PERMISSIONS.get(role, {})

    @classmethod
    def get_roles_with_permission(cls, operation: FileOperation) -> List[str]:
        """Get all roles that have a specific permission"""
        return [role for role, perms in cls.ROLE_PERMISSIONS.items() 
                if perms.get(operation, False)]

    @classmethod
    def can_manage_role(cls, admin_role: str, target_role: str) -> bool:
        """Check if admin_role can manage users with target_role"""
        # Root can manage all roles except other roots
        if admin_role == "root":
            return target_role != "root"
            
        # Check role hierarchy
        if admin_role in cls.ROLE_HIERARCHY:
            return target_role in cls.ROLE_HIERARCHY[admin_role]
            
        return False

    @classmethod
    def get_manageable_roles(cls, admin_role: str) -> List[str]:
        """Get list of roles that can be managed by admin_role"""
        return cls.ROLE_HIERARCHY.get(admin_role, [])

class SecurityManager:
    def __init__(self, salt_file: str = "salt.key", log_file: str = "security.log"):
        """Initialize SecurityManager with a salt file for key derivation"""
        self.salt_file = salt_file
        self._setup_logging(log_file)
        self._ensure_salt()
        # Load and store salt at initialization
        self._salt = self._load_salt()
        
    def _setup_logging(self, log_file: str) -> None:
        """Setup security event logging"""
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        # Configure logging
        self.logger = logging.getLogger('security_manager')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
        
    def _log_security_event(self, event_type: str, details: str, level: str = "INFO") -> None:
        """Log security event"""
        log_method = getattr(self.logger, level.lower())
        log_method(f"{event_type}: {details}")

    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        Returns: (is_valid: bool, message: str)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
            
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
            
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
            
        if not re.search(r"\d", password):
            return False, "Password must contain at least one number"
            
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character"
            
        return True, "Password meets complexity requirements"
        
    def _ensure_salt(self) -> None:
        """Ensure salt file exists or create it"""
        os.makedirs(os.path.dirname(self.salt_file), exist_ok=True)
        if not os.path.exists(self.salt_file):
            with open(self.salt_file, 'wb') as f:
                f.write(os.urandom(32))  # 32 bytes salt for PBKDF2
    
    def _load_salt(self) -> bytes:
        """Load or create salt"""
        try:
            with open(self.salt_file, 'rb') as f:
                salt = f.read()
                if len(salt) != 32:  # Validate salt length
                    salt = os.urandom(32)
                    with open(self.salt_file, 'wb') as f:
                        f.write(salt)
                return salt
        except Exception:
            # If any error occurs, create new salt
            salt = os.urandom(32)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            return salt
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,  # Use stored salt
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def encrypt_file(self, data: dict, password: str) -> bytes:
        """Encrypt data with password"""
        try:
            # Convert data to JSON string
            json_data = json.dumps(data).encode()
            
            # Derive key and create AESGCM instance
            key = self._derive_key(password)
            aesgcm = AESGCM(key)
            
            # Generate nonce
            nonce = os.urandom(12)
            
            # Encrypt data
            encrypted_data = aesgcm.encrypt(nonce, json_data, None)
            
            # Combine nonce and encrypted data
            self._log_security_event("ENCRYPTION", "File encryption successful")
            return b64encode(nonce + encrypted_data)
        except Exception as e:
            self._log_security_event("ENCRYPTION_ERROR", str(e), "ERROR")
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt_file(self, encrypted_data: bytes, password: str) -> dict:
        """Decrypt data with password"""
        try:
            # Decode from base64
            raw_data = b64decode(encrypted_data)
            
            # Extract nonce and ciphertext
            nonce = raw_data[:12]
            ciphertext = raw_data[12:]
            
            # Derive key and create AESGCM instance
            key = self._derive_key(password)
            aesgcm = AESGCM(key)
            
            # Decrypt data
            decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
            
            # Parse JSON
            self._log_security_event("DECRYPTION", "File decryption successful")
            return json.loads(decrypted_data.decode())
        except Exception as e:
            self._log_security_event("DECRYPTION_ERROR", str(e), "ERROR")
            raise ValueError(f"Decryption failed. Invalid password or corrupted data: {str(e)}")
    
    def hash_password(self, password: str) -> bytes:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    def verify_password(self, password: str, hashed: bytes) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode(), hashed)
    
    def create_session_token(self, user_data: dict) -> Tuple[str, datetime]:
        """Create a session token for user"""
        # Create token with timestamp and user data
        timestamp = datetime.now(UTC)
        expiry = timestamp + timedelta(hours=24)
        
        token_data = {
            "email": user_data["email"],
            "role": user_data["role"],
            "created_at": timestamp.isoformat(),
            "expires_at": expiry.isoformat()
        }
        
        # Encrypt token data with a random key
        token_key = os.urandom(32)
        aesgcm = AESGCM(token_key)
        nonce = os.urandom(12)
        
        token_bytes = json.dumps(token_data).encode()
        encrypted_token = aesgcm.encrypt(nonce, token_bytes, None)
        
        # Combine key, nonce and encrypted data
        token = b64encode(token_key + nonce + encrypted_token).decode()
        
        return token, expiry
    
    def verify_session_token(self, token: str) -> Optional[dict]:
        """Verify and decode session token"""
        try:
            # Decode token
            raw_data = b64decode(token.encode())
            
            # Extract components
            token_key = raw_data[:32]
            nonce = raw_data[32:44]
            encrypted_data = raw_data[44:]
            
            # Decrypt token data
            aesgcm = AESGCM(token_key)
            decrypted_data = aesgcm.decrypt(nonce, encrypted_data, None)
            token_data = json.loads(decrypted_data.decode())
            
            # Validate token structure
            required_fields = ["email", "role", "created_at", "expires_at"]
            if not all(field in token_data for field in required_fields):
                self._log_security_event(
                    "TOKEN_ERROR",
                    "Invalid token structure - missing required fields",
                    "ERROR"
                )
                return None
            
            # Check expiration
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(UTC) > expires_at:
                self._log_security_event(
                    "TOKEN_EXPIRED",
                    f"Token expired at {expires_at}",
                    "WARNING"
                )
                return None
            
            self._log_security_event(
                "TOKEN_VERIFIED",
                f"Token verified for user {token_data['email']}"
            )
            return token_data
            
        except Exception as e:
            self._log_security_event(
                "TOKEN_ERROR",
                f"Token verification failed: {str(e)}",
                "ERROR"
            )
            return None 