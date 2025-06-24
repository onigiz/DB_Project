import os
import json
import pandas as pd
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple
from .security_manager import SecurityManager, FileOperation, FilePermissions
from .logging_config import LogConfig

class SchemaManager:
    def __init__(self, security_manager: SecurityManager, 
                 schemas_dir: str = "data/schemas",
                 active_schema_file: str = "active_schema.enc"):
        """Initialize SchemaManager with SecurityManager instance"""
        self.security_manager = security_manager
        self.schemas_dir = schemas_dir
        self.active_schema_file = os.path.join(schemas_dir, active_schema_file)
        self.master_password = os.getenv("MASTER_PASSWORD", "default_master_password")
        
        # Setup logging
        self.logger = LogConfig.get_logger('schema_manager', 'schema.log')
        
        # Ensure schemas directory exists
        os.makedirs(self.schemas_dir, exist_ok=True)
    
    def _log_event(self, event_type: str, details: str, level: str = "INFO") -> None:
        """Log schema event"""
        log_method = getattr(self.logger, level.lower())
        log_method(f"{event_type}: {details}")

    def _save_schema(self, schema_data: dict, schema_file: str) -> None:
        """Save schema to encrypted file"""
        encrypted_data = self.security_manager.encrypt_file(schema_data, self.master_password)
        with open(schema_file, 'wb') as f:
            f.write(encrypted_data)

    def _load_schema(self, schema_file: str) -> dict:
        """Load schema from encrypted file"""
        try:
            with open(schema_file, 'rb') as f:
                encrypted_data = f.read()
            return self.security_manager.decrypt_file(encrypted_data, self.master_password)
        except FileNotFoundError:
            return {"columns": [], "metadata": {"version": "1.0", "created_at": None, "created_by": None}}

    def create_schema(self, token: str, schema_name: str, columns: List[Dict]) -> Tuple[bool, str]:
        """Create a new schema"""
        if not FilePermissions.has_permission(
            self.security_manager.verify_session_token(token)["role"],
            FileOperation.SCHEMA_MODIFY
        ):
            self._log_event("SCHEMA_CREATE_FAILED", "Insufficient permissions", "ERROR")
            return False, "Insufficient permissions"

        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            # Validate schema name
            if not schema_name.isalnum():
                return False, "Schema name must be alphanumeric"
            
            schema_file = os.path.join(self.schemas_dir, f"{schema_name}.enc")
            if os.path.exists(schema_file):
                return False, "Schema with this name already exists"
            
            # Create schema data
            schema_data = {
                "columns": columns,
                "metadata": {
                    "version": "1.0",
                    "created_at": datetime.now(UTC).isoformat(),
                    "created_by": user_email,
                    "name": schema_name
                }
            }
            
            # Save schema
            self._save_schema(schema_data, schema_file)
            
            self._log_event(
                "SCHEMA_CREATED",
                f"Schema '{schema_name}' created by {user_email}"
            )
            return True, "Schema created successfully"
            
        except Exception as e:
            error_msg = f"Error creating schema: {str(e)}"
            self._log_event("SCHEMA_CREATE_ERROR", error_msg, "ERROR")
            return False, error_msg

    def import_schema_from_json(self, token: str, schema_name: str, json_file: str) -> Tuple[bool, str]:
        """Import schema from JSON file"""
        if not FilePermissions.has_permission(
            self.security_manager.verify_session_token(token)["role"],
            FileOperation.SCHEMA_MODIFY
        ):
            return False, "Insufficient permissions"

        try:
            # Load and validate JSON
            with open(json_file, 'r') as f:
                schema_def = json.load(f)
            
            if not isinstance(schema_def, dict) or "columns" not in schema_def:
                return False, "Invalid schema format"
            
            # Create schema using the loaded definition
            return self.create_schema(token, schema_name, schema_def["columns"])
            
        except Exception as e:
            error_msg = f"Error importing schema from JSON: {str(e)}"
            self._log_event("SCHEMA_IMPORT_ERROR", error_msg, "ERROR")
            return False, error_msg

    def import_schema_from_excel(self, token: str, schema_name: str, excel_file: str) -> Tuple[bool, str]:
        """Import schema from Excel file structure"""
        if not FilePermissions.has_permission(
            self.security_manager.verify_session_token(token)["role"],
            FileOperation.SCHEMA_MODIFY
        ):
            return False, "Insufficient permissions"

        try:
            # Read Excel file
            df = pd.read_excel(excel_file)
            
            # Convert Excel columns to schema definition
            columns = []
            for col in df.columns:
                dtype = str(df[col].dtype)
                column_def = {
                    "name": col,
                    "type": "TEXT" if dtype == "object" else "NUMBER" if dtype.startswith(("int", "float")) else "TEXT",
                    "nullable": df[col].isnull().any(),
                    "excel_column": col
                }
                columns.append(column_def)
            
            # Create schema using the extracted column definitions
            return self.create_schema(token, schema_name, columns)
            
        except Exception as e:
            error_msg = f"Error importing schema from Excel: {str(e)}"
            self._log_event("SCHEMA_IMPORT_ERROR", error_msg, "ERROR")
            return False, error_msg

    def list_schemas(self, token: str) -> List[Dict]:
        """List all available schemas"""
        try:
            schemas = []
            for file in os.listdir(self.schemas_dir):
                if file.endswith('.enc'):
                    schema_data = self._load_schema(os.path.join(self.schemas_dir, file))
                    schemas.append(schema_data["metadata"])
            return schemas
        except Exception as e:
            self._log_event("SCHEMA_LIST_ERROR", str(e), "ERROR")
            return []

    def get_schema(self, token: str, schema_name: str) -> Optional[Dict]:
        """Get a specific schema by name"""
        try:
            schema_file = os.path.join(self.schemas_dir, f"{schema_name}.enc")
            return self._load_schema(schema_file)
        except Exception as e:
            self._log_event("SCHEMA_GET_ERROR", str(e), "ERROR")
            return None

    def set_active_schema(self, token: str, schema_name: str) -> Tuple[bool, str]:
        """Set the active schema for the database"""
        if not FilePermissions.has_permission(
            self.security_manager.verify_session_token(token)["role"],
            FileOperation.SCHEMA_MODIFY
        ):
            return False, "Insufficient permissions"

        try:
            # Get user email from token
            token_data = self.security_manager.verify_session_token(token)
            user_email = token_data["email"]
            
            # Load the specified schema
            schema_file = os.path.join(self.schemas_dir, f"{schema_name}.enc")
            if not os.path.exists(schema_file):
                return False, "Schema does not exist"
            
            schema_data = self._load_schema(schema_file)
            
            # Update active schema
            active_schema = {
                "schema": schema_data,
                "metadata": {
                    "activated_at": datetime.now(UTC).isoformat(),
                    "activated_by": user_email,
                    "name": schema_name
                }
            }
            
            self._save_schema(active_schema, self.active_schema_file)
            
            self._log_event(
                "SCHEMA_ACTIVATED",
                f"Schema '{schema_name}' set as active by {user_email}"
            )
            return True, "Active schema updated successfully"
            
        except Exception as e:
            error_msg = f"Error setting active schema: {str(e)}"
            self._log_event("SCHEMA_ACTIVATE_ERROR", error_msg, "ERROR")
            return False, error_msg

    def get_active_schema(self, token: str) -> Optional[Dict]:
        """Get the currently active schema"""
        try:
            if os.path.exists(self.active_schema_file):
                active_schema = self._load_schema(self.active_schema_file)
                return active_schema["schema"]
            return None
        except Exception as e:
            self._log_event("ACTIVE_SCHEMA_GET_ERROR", str(e), "ERROR")
            return None

    def export_schema_to_json(self, token: str, schema_name: str, output_file: str) -> Tuple[bool, str]:
        """Export schema to JSON file"""
        try:
            schema_data = self.get_schema(token, schema_name)
            if not schema_data:
                return False, "Schema not found"
            
            with open(output_file, 'w') as f:
                json.dump(schema_data, f, indent=2)
            
            self._log_event(
                "SCHEMA_EXPORTED",
                f"Schema '{schema_name}' exported to JSON"
            )
            return True, "Schema exported successfully"
            
        except Exception as e:
            error_msg = f"Error exporting schema: {str(e)}"
            self._log_event("SCHEMA_EXPORT_ERROR", error_msg, "ERROR")
            return False, error_msg 