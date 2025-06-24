import os
import json
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .security_manager import SecurityManager, FileOperation, FilePermissions

class DataManager:
    def __init__(self, security_manager: SecurityManager, 
                 schema_file: str = "schema.enc",
                 data_file: str = "database.enc"):
        """Initialize DataManager with SecurityManager instance"""
        self.security_manager = security_manager
        self.schema_file = schema_file
        self.data_file = data_file
        self.master_password = os.getenv("MASTER_PASSWORD", "default_master_password")
        self.config_file = "db_config.enc"
        
        # Setup logging
        self._setup_logging()
        self._load_config()
    
    def _setup_logging(self) -> None:
        """Setup database operations logging"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure logging
        self.logger = logging.getLogger('database_manager')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        handler = logging.FileHandler(os.path.join(log_dir, "database_operations.log"))
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(handler)
    
    def _log_db_event(self, event_type: str, details: str, level: str = "INFO") -> None:
        """Log database event"""
        log_method = getattr(self.logger, level.lower())
        log_method(f"{event_type}: {details}")
    
    def _load_config(self) -> None:
        """Load database configuration"""
        try:
            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()
            config = self.security_manager.decrypt_file(encrypted_data, self.master_password)
            self.data_file = config.get("data_file", self.data_file)
            self.schema_file = config.get("schema_file", self.schema_file)
            self.master_password = config.get("master_password", self.master_password)
        except (FileNotFoundError, ValueError):
            # If file doesn't exist or is corrupted, create a new one with default values
            self._save_config()
        except Exception as e:
            print(f"Warning: Could not load database configuration: {str(e)}")
            print("Using default configuration...")
    
    def _save_config(self) -> None:
        """Save database configuration"""
        config = {
            "data_file": self.data_file,
            "schema_file": self.schema_file,
            "master_password": self.master_password
        }
        encrypted_data = self.security_manager.encrypt_file(config, self.master_password)
        with open(self.config_file, 'wb') as f:
            f.write(encrypted_data)
    
    def _check_permission(self, token: str, operation: FileOperation) -> bool:
        """Check if user has permission for operation"""
        token_data = self.security_manager.verify_session_token(token)
        if not token_data:
            return False
        return FilePermissions.has_permission(token_data["role"], operation)

    def _can_modify_data(self, token: str) -> bool:
        """Check if user has permission to modify data"""
        return self._check_permission(token, FileOperation.WRITE)
    
    def _can_modify_schema(self, token: str) -> bool:
        """Check if user has permission to modify schema"""
        return self._check_permission(token, FileOperation.SCHEMA_MODIFY)
    
    def _can_delete_data(self, token: str) -> bool:
        """Check if user has permission to delete data"""
        return self._check_permission(token, FileOperation.DELETE)
    
    def _load_schema(self) -> dict:
        """Load schema from encrypted file"""
        try:
            with open(self.schema_file, 'rb') as f:
                encrypted_data = f.read()
            return self.security_manager.decrypt_file(encrypted_data, self.master_password)
        except FileNotFoundError:
            return {"column_definitions": [], "last_modified": None}
    
    def _save_schema(self, schema: dict) -> None:
        """Save schema to encrypted file"""
        encrypted_data = self.security_manager.encrypt_file(schema, self.master_password)
        with open(self.schema_file, 'wb') as f:
            f.write(encrypted_data)
    
    def _load_data(self) -> dict:
        """Load data from encrypted file"""
        try:
            with open(self.data_file, 'rb') as f:
                encrypted_data = f.read()
            return self.security_manager.decrypt_file(encrypted_data, self.master_password)
        except FileNotFoundError:
            return {"data": [], "metadata": {"version": "1.0", "last_updated": None, "updated_by": None, "row_count": 0}}
    
    def _save_data(self, database: dict) -> None:
        """Save data to encrypted file"""
        encrypted_data = self.security_manager.encrypt_file(database, self.master_password)
        with open(self.data_file, 'wb') as f:
            f.write(encrypted_data)
    
    def update_schema(self, token: str, column_definitions: List[Dict]) -> bool:
        """Update schema with new column definitions (admin only)"""
        if not self._can_modify_schema(token):
            self._log_db_event("SCHEMA_UPDATE_FAILED", "Insufficient permissions", "ERROR")
            return False
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            schema = {
                "column_definitions": column_definitions,
                "last_modified": datetime.utcnow().isoformat(),
                "modified_by": user_email
            }
            self._save_schema(schema)
            
            self._log_db_event("SCHEMA_UPDATED", f"Schema updated by {user_email}")
            return True
        except Exception as e:
            self._log_db_event("SCHEMA_UPDATE_ERROR", str(e), "ERROR")
            return False
    
    def get_schema(self) -> List[Dict]:
        """Get current schema (all users)"""
        schema = self._load_schema()
        return schema.get("column_definitions", [])
    
    def process_excel(self, token: str, file_path: str) -> Tuple[bool, str]:
        """Process Excel file according to schema"""
        if not self._can_modify_data(token):
            self._log_db_event("EXCEL_PROCESS_FAILED", "Insufficient permissions", "ERROR")
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            self._log_db_event("EXCEL_PROCESSING", f"Starting Excel processing: {file_path}")
            
            # Load schema
            schema = self._load_schema()
            if not schema["column_definitions"]:
                self._log_db_event("EXCEL_PROCESS_FAILED", "Schema not defined", "ERROR")
                return False, "Schema not defined"
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate columns
            excel_columns = set(df.columns)
            required_columns = {col_def["excel_column"] for col_def in schema["column_definitions"]}
            missing_columns = required_columns - excel_columns
            if missing_columns:
                error_msg = f"Missing columns in Excel: {missing_columns}"
                self._log_db_event("EXCEL_VALIDATION_ERROR", error_msg, "ERROR")
                return False, error_msg
            
            self._log_db_event("EXCEL_PROCESSED", f"Excel file processed successfully by {user_email}")
            return True, "Excel file processed successfully"
            
        except Exception as e:
            error_msg = f"Error processing Excel file: {str(e)}"
            self._log_db_event("EXCEL_PROCESS_ERROR", error_msg, "ERROR")
            return False, error_msg
    
    def get_data(self, page: int = 1, page_size: int = 100) -> Dict:
        """Get data with pagination (all users)"""
        database = self._load_data()
        data = database["data"]
        
        # Calculate pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return {
            "data": data[start_idx:end_idx],
            "metadata": database["metadata"],
            "pagination": {
                "total_records": len(data),
                "total_pages": (len(data) + page_size - 1) // page_size,
                "current_page": page,
                "page_size": page_size
            }
        }
    
    def update_record(self, token: str, record_index: int, updated_data: Dict) -> Tuple[bool, str]:
        """Update a specific record in the database"""
        if not self._can_modify_data(token):
            self._log_db_event("RECORD_UPDATE_FAILED", "Insufficient permissions", "ERROR")
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            database = self._load_data()
            if record_index < 0 or record_index >= len(database["data"]):
                self._log_db_event("RECORD_UPDATE_FAILED", f"Invalid record index: {record_index}", "ERROR")
                return False, "Invalid record index"
            
            # Update record
            old_data = database["data"][record_index].copy()
            database["data"][record_index].update(updated_data)
            
            # Update metadata
            database["metadata"]["last_updated"] = datetime.utcnow().isoformat()
            database["metadata"]["updated_by"] = user_email
            
            self._save_data(database)
            
            self._log_db_event(
                "RECORD_UPDATED", 
                f"Record #{record_index} updated by {user_email}. Changes: {updated_data}"
            )
            return True, "Record updated successfully"
            
        except Exception as e:
            error_msg = f"Error updating record: {str(e)}"
            self._log_db_event("RECORD_UPDATE_ERROR", error_msg, "ERROR")
            return False, error_msg
    
    def add_record(self, token: str, record_data: Dict) -> Tuple[bool, str]:
        """Add a new record to the database (admin/moderator only)"""
        if not self._can_modify_data(token):
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            # Validate record against schema
            schema = self._load_schema()
            required_fields = {col_def["name"] for col_def in schema["column_definitions"]}
            missing_fields = required_fields - set(record_data.keys())
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"
            
            database = self._load_data()
            
            # Add new record
            database["data"].append(record_data)
            
            # Update metadata
            database["metadata"]["last_updated"] = datetime.utcnow().isoformat()
            database["metadata"]["updated_by"] = user_email
            database["metadata"]["row_count"] = len(database["data"])
            
            self._save_data(database)
            return True, "Record added successfully"
            
        except Exception as e:
            return False, f"Error adding record: {str(e)}"
    
    def delete_record(self, token: str, record_index: int) -> Tuple[bool, str]:
        """Delete a record from the database"""
        if not self._can_delete_data(token):
            self._log_db_event("RECORD_DELETE_FAILED", "Insufficient permissions for deletion", "ERROR")
            return False, "Insufficient permissions for deletion"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            database = self._load_data()
            if record_index < 0 or record_index >= len(database["data"]):
                self._log_db_event("RECORD_DELETE_FAILED", f"Invalid record index: {record_index}", "ERROR")
                return False, "Invalid record index"
            
            # Store record for logging
            deleted_record = database["data"][record_index]
            
            # Remove record
            del database["data"][record_index]
            
            # Update metadata
            database["metadata"]["last_updated"] = datetime.utcnow().isoformat()
            database["metadata"]["updated_by"] = user_email
            database["metadata"]["row_count"] = len(database["data"])
            
            self._save_data(database)
            
            self._log_db_event(
                "RECORD_DELETED", 
                f"Record #{record_index} deleted by {user_email}. Record data: {deleted_record}"
            )
            return True, "Record deleted successfully"
            
        except Exception as e:
            error_msg = f"Error deleting record: {str(e)}"
            self._log_db_event("RECORD_DELETE_ERROR", error_msg, "ERROR")
            return False, error_msg
    
    def update_database_config(self, token: str, directory: str, new_password: str) -> Tuple[bool, str]:
        """Update database location and master password"""
        token_data = self.security_manager.verify_session_token(token)
        if not token_data or token_data["role"] not in ["root", "admin"]:
            return False, "Insufficient permissions"
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # Define new file paths
            new_data_file = os.path.join(directory, "database.enc")
            new_schema_file = os.path.join(directory, "schema.enc")
            
            # Load current data with old password
            current_data = self._load_data()
            current_schema = self._load_schema()
            
            # Update paths and password
            old_data_file = self.data_file
            old_schema_file = self.schema_file
            old_password = self.master_password
            
            self.data_file = new_data_file
            self.schema_file = new_schema_file
            self.master_password = new_password
            
            # Save data with new password
            self._save_data(current_data)
            self._save_schema(current_schema)
            self._save_config()
            
            # Delete old files if they exist and are different
            if os.path.exists(old_data_file) and old_data_file != new_data_file:
                os.remove(old_data_file)
            if os.path.exists(old_schema_file) and old_schema_file != new_schema_file:
                os.remove(old_schema_file)
            
            return True, "Database configuration updated successfully"
        except Exception as e:
            # Restore old configuration if something goes wrong
            self.data_file = old_data_file
            self.schema_file = old_schema_file
            self.master_password = old_password
            self._save_config()
            return False, f"Error updating database configuration: {str(e)}" 