import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .security_manager import SecurityManager

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
        self._load_config()
    
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
    
    def _can_modify_data(self, token: str) -> bool:
        """Check if user has permission to modify data"""
        token_data = self.security_manager.verify_session_token(token)
        if not token_data:
            return False
        return token_data["role"] in ["admin", "moderator"]
    
    def _can_modify_schema(self, token: str) -> bool:
        """Check if user has permission to modify schema"""
        token_data = self.security_manager.verify_session_token(token)
        if not token_data:
            return False
        return token_data["role"] == "admin"
    
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
            return False
            
        try:
            schema = {
                "column_definitions": column_definitions,
                "last_modified": datetime.utcnow().isoformat(),
            }
            self._save_schema(schema)
            return True
        except Exception as e:
            print(f"Error updating schema: {e}")
            return False
    
    def get_schema(self) -> List[Dict]:
        """Get current schema (all users)"""
        schema = self._load_schema()
        return schema.get("column_definitions", [])
    
    def process_excel(self, token: str, file_path: str) -> Tuple[bool, str]:
        """Process Excel file according to schema (admin/moderator only)"""
        if not self._can_modify_data(token):
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            # Load schema
            schema = self._load_schema()
            if not schema["column_definitions"]:
                return False, "Schema not defined"
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Validate columns exist
            excel_columns = set(df.columns)
            required_columns = {col_def["excel_column"] for col_def in schema["column_definitions"]}
            missing_columns = required_columns - excel_columns
            if missing_columns:
                return False, f"Missing columns in Excel: {missing_columns}"
            
            # Transform data according to schema
            transformed_data = []
            for _, row in df.iterrows():
                record = {}
                for col_def in schema["column_definitions"]:
                    excel_col = col_def["excel_column"]
                    target_name = col_def["name"]
                    data_type = col_def.get("data_type", "string")
                    
                    value = row[excel_col]
                    
                    # Handle data type conversions
                    if data_type == "date" and pd.notna(value):
                        value = pd.to_datetime(value).isoformat()
                    elif data_type == "number" and pd.notna(value):
                        value = float(value)
                    elif pd.isna(value):
                        value = None
                    else:
                        value = str(value)
                    
                    record[target_name] = value
                transformed_data.append(record)
            
            # Load existing data
            database = self._load_data()
            
            # Update data
            database["data"] = transformed_data
            database["metadata"] = {
                "version": "1.0",
                "last_updated": datetime.utcnow().isoformat(),
                "updated_by": user_email,
                "row_count": len(transformed_data)
            }
            
            # Save updated data
            self._save_data(database)
            
            return True, f"Successfully processed {len(transformed_data)} records"
            
        except Exception as e:
            return False, f"Error processing Excel file: {str(e)}"
    
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
        """Update a specific record in the database (admin/moderator only)"""
        if not self._can_modify_data(token):
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            database = self._load_data()
            if record_index < 0 or record_index >= len(database["data"]):
                return False, "Invalid record index"
            
            # Update record
            database["data"][record_index].update(updated_data)
            
            # Update metadata
            database["metadata"]["last_updated"] = datetime.utcnow().isoformat()
            database["metadata"]["updated_by"] = user_email
            
            self._save_data(database)
            return True, "Record updated successfully"
            
        except Exception as e:
            return False, f"Error updating record: {str(e)}"
    
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
        """Delete a record from the database (admin/moderator only)"""
        if not self._can_modify_data(token):
            return False, "Insufficient permissions"
            
        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            database = self._load_data()
            if record_index < 0 or record_index >= len(database["data"]):
                return False, "Invalid record index"
            
            # Remove record
            del database["data"][record_index]
            
            # Update metadata
            database["metadata"]["last_updated"] = datetime.utcnow().isoformat()
            database["metadata"]["updated_by"] = user_email
            database["metadata"]["row_count"] = len(database["data"])
            
            self._save_data(database)
            return True, "Record deleted successfully"
            
        except Exception as e:
            return False, f"Error deleting record: {str(e)}"
    
    def update_database_config(self, token: str, directory: str, new_password: str) -> Tuple[bool, str]:
        """Update database location and master password"""
        token_data = self.security_manager.verify_session_token(token)
        if not token_data or token_data["role"] != "admin":
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