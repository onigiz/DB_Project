import os
import json
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from base64 import b64encode, b64decode

class SecurityManager:
    def __init__(self, salt_file: str = "salt.key"):
        """Initialize SecurityManager with a salt file for key derivation"""
        self.salt_file = salt_file
        self._ensure_salt()
        
    def _ensure_salt(self) -> None:
        """Ensure salt file exists or create it"""
        if not os.path.exists(self.salt_file):
            with open(self.salt_file, 'wb') as f:
                f.write(os.urandom(32))  # 32 bytes salt for PBKDF2
    
    def _get_salt(self) -> bytes:
        """Read salt from file"""
        with open(self.salt_file, 'rb') as f:
            return f.read()
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._get_salt(),
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def encrypt_file(self, data: dict, password: str) -> bytes:
        """Encrypt data with password"""
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
        return b64encode(nonce + encrypted_data)
    
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
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise ValueError("Decryption failed. Invalid password or corrupted data.") from e
    
    def hash_password(self, password: str) -> bytes:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    def verify_password(self, password: str, hashed: bytes) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode(), hashed)
    
    def create_session_token(self, user_data: dict) -> Tuple[str, datetime]:
        """Create a session token for user"""
        # Create token with timestamp and user data
        timestamp = datetime.utcnow()
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
            
            # Check expiry
            expiry = datetime.fromisoformat(token_data["expires_at"])
            if expiry < datetime.utcnow():
                return None
                
            return token_data
        except Exception:
            return None 