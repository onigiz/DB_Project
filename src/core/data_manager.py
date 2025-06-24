import os
import json
import pandas as pd
import logging
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple
from .security_manager import SecurityManager, FileOperation, FilePermissions
from .schema_manager import SchemaManager

class DataManager:
    def __init__(self, security_manager: SecurityManager, 
                 schema_manager: SchemaManager,
                 data_file: str = "database.enc"):
        """Initialize DataManager with SecurityManager and SchemaManager instances"""
        self.security_manager = security_manager
        self.schema_manager = schema_manager
        self.data_file = data_file
        self.master_password = os.getenv("MASTER_PASSWORD", "default_master_password")
        self.config_file = os.path.join("data", "config", "db_config.enc")
        
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
    
    def _can_delete_data(self, token: str) -> bool:
        """Check if user has permission to delete data"""
        return self._check_permission(token, FileOperation.DELETE)
    
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
    
    def process_excel(self, token: str, file_path: str) -> Tuple[bool, str]:
        """Process Excel file according to active schema"""
        if not self._can_modify_data(token):
            self._log_db_event("EXCEL_PROCESS_FAILED", "Insufficient permissions", "ERROR")
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            self._log_db_event("EXCEL_PROCESSING", f"Starting Excel processing: {file_path}")
            
            # Load active schema
            active_schema = self.schema_manager.get_active_schema(token)
            if not active_schema:
                self._log_db_event("EXCEL_PROCESS_FAILED", "No active schema defined", "ERROR")
                return False, "No active schema defined"
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate columns against schema
            schema_columns = {col["excel_column"] for col in active_schema["columns"]}
            excel_columns = set(df.columns)
            missing_columns = schema_columns - excel_columns
            if missing_columns:
                error_msg = f"Missing columns in Excel: {missing_columns}"
                self._log_db_event("EXCEL_VALIDATION_ERROR", error_msg, "ERROR")
                return False, error_msg
            
            # Process data according to schema
            processed_data = []
            for _, row in df.iterrows():
                record = {}
                for col_def in active_schema["columns"]:
                    excel_col = col_def["excel_column"]
                    db_col = col_def["name"]
                    value = row[excel_col]
                    
                    # Validate data type
                    if col_def["type"] == "NUMBER" and not pd.isna(value):
                        try:
                            value = float(value)
                        except ValueError:
                            return False, f"Invalid number format in column {excel_col}"
                    
                    # Handle null values
                    if pd.isna(value):
                        if not col_def.get("nullable", False):
                            return False, f"Null value not allowed in column {excel_col}"
                        value = None
                    
                    record[db_col] = value
                processed_data.append(record)
            
            # Load current database
            database = self._load_data()
            
            # Add new records
            database["data"].extend(processed_data)
            
            # Update metadata
            database["metadata"].update({
                "last_updated": datetime.now(UTC).isoformat(),
                "updated_by": user_email,
                "row_count": len(database["data"]),
                "active_schema": active_schema["metadata"]["name"]
            })
            
            # Save updated database
            self._save_data(database)
            
            self._log_db_event(
                "EXCEL_PROCESSED",
                f"Excel file processed successfully by {user_email}. Added {len(processed_data)} records."
            )
            return True, f"Excel file processed successfully. Added {len(processed_data)} records."
            
        except Exception as e:
            error_msg = f"Error processing Excel file: {str(e)}"
            self._log_db_event("EXCEL_PROCESS_ERROR", error_msg, "ERROR")
            return False, error_msg
    
    def get_data(self, token: str, page: int = 1, page_size: int = 100) -> Dict:
        """Get data with pagination"""
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
    
    def add_record(self, token: str, record_data: Dict) -> Tuple[bool, str]:
        """Add a new record to the database"""
        if not self._can_modify_data(token):
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            # Load active schema
            active_schema = self.schema_manager.get_active_schema(token)
            if not active_schema:
                return False, "No active schema defined"
            
            # Validate record against schema
            schema_columns = {col["name"] for col in active_schema["columns"]}
            record_columns = set(record_data.keys())
            
            # Check for missing required fields
            missing_fields = schema_columns - record_columns
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"
            
            # Validate data types and constraints
            for col_def in active_schema["columns"]:
                value = record_data.get(col_def["name"])
                
                # Check null constraint
                if value is None and not col_def.get("nullable", False):
                    return False, f"Null value not allowed in column {col_def['name']}"
                
                # Validate data type
                if value is not None and col_def["type"] == "NUMBER":
                    try:
                        record_data[col_def["name"]] = float(value)
                    except ValueError:
                        return False, f"Invalid number format in column {col_def['name']}"
            
            database = self._load_data()
            
            # Add new record
            database["data"].append(record_data)
            
            # Update metadata
            database["metadata"].update({
                "last_updated": datetime.now(UTC).isoformat(),
                "updated_by": user_email,
                "row_count": len(database["data"]),
                "active_schema": active_schema["metadata"]["name"]
            })
            
            self._save_data(database)
            return True, "Record added successfully"
            
        except Exception as e:
            return False, f"Error adding record: {str(e)}"
    
    def update_record(self, token: str, record_index: int, updated_data: Dict) -> Tuple[bool, str]:
        """Update a specific record in the database"""
        if not self._can_modify_data(token):
            self._log_db_event("RECORD_UPDATE_FAILED", "Insufficient permissions", "ERROR")
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            # Load active schema
            active_schema = self.schema_manager.get_active_schema(token)
            if not active_schema:
                return False, "No active schema defined"
            
            database = self._load_data()
            if record_index < 0 or record_index >= len(database["data"]):
                self._log_db_event("RECORD_UPDATE_FAILED", f"Invalid record index: {record_index}", "ERROR")
                return False, "Invalid record index"
            
            # Validate updated data against schema
            for col_def in active_schema["columns"]:
                if col_def["name"] in updated_data:
                    value = updated_data[col_def["name"]]
                    
                    # Check null constraint
                    if value is None and not col_def.get("nullable", False):
                        return False, f"Null value not allowed in column {col_def['name']}"
                    
                    # Validate data type
                    if value is not None and col_def["type"] == "NUMBER":
                        try:
                            updated_data[col_def["name"]] = float(value)
                        except ValueError:
                            return False, f"Invalid number format in column {col_def['name']}"
            
            # Update record
            old_data = database["data"][record_index].copy()
            database["data"][record_index].update(updated_data)
            
            # Update metadata
            database["metadata"].update({
                "last_updated": datetime.now(UTC).isoformat(),
                "updated_by": user_email
            })
            
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
            database["metadata"].update({
                "last_updated": datetime.now(UTC).isoformat(),
                "updated_by": user_email,
                "row_count": len(database["data"])
            })
            
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