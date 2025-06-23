#!/usr/bin/env python3
import os
import sys
import shutil
from getpass import getpass
import json
from pathlib import Path
import stat
from datetime import datetime, UTC
from core.security_manager import SecurityManager
from core.user_manager import UserManager

def log_step(message: str) -> None:
    """Print a step log message"""
    print(f"\n[STEP] {message}")

def log_info(message: str) -> None:
    """Print an info log message"""
    print(f"[INFO] {message}")

def log_warning(message: str) -> None:
    """Print a warning log message"""
    print(f"[WARNING] {message}")

def log_error(message: str) -> None:
    """Print an error log message"""
    print(f"[ERROR] {message}")

def ensure_directory(directory):
    """Create directory if it doesn't exist, clear it if it does"""
    try:
        log_info(f"Processing directory: {directory}")
        
        # If directory exists, try to remove it safely
        if os.path.exists(directory):
            log_info(f"Removing existing directory: {directory}")
            try:
                # First try to remove all files
                for root, dirs, files in os.walk(directory, topdown=False):
                    for name in files:
                        try:
                            file_path = os.path.join(root, name)
                            if os.path.exists(file_path):
                                os.chmod(file_path, 0o777)  # Give all permissions
                                os.unlink(file_path)
                                log_info(f"Removed file: {file_path}")
                        except Exception as e:
                            log_warning(f"Could not remove file {name}: {e}")
                    
                    # Then try to remove directories
                    for name in dirs:
                        try:
                            dir_path = os.path.join(root, name)
                            if os.path.exists(dir_path):
                                os.chmod(dir_path, 0o777)  # Give all permissions
                                os.rmdir(dir_path)
                                log_info(f"Removed directory: {dir_path}")
                        except Exception as e:
                            log_warning(f"Could not remove directory {name}: {e}")
                
                # Finally remove the root directory
                if os.path.exists(directory):
                    os.chmod(directory, 0o777)  # Give all permissions
                    os.rmdir(directory)
                    log_info(f"Removed root directory: {directory}")
            except Exception as e:
                log_warning(f"Could not fully remove directory {directory}: {e}")
                # If we can't remove it, try to clean its contents
                try:
                    for item in os.listdir(directory):
                        item_path = os.path.join(directory, item)
                        try:
                            if os.path.isfile(item_path):
                                os.chmod(item_path, 0o777)
                                os.unlink(item_path)
                                log_info(f"Removed file: {item_path}")
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path, ignore_errors=True)
                                log_info(f"Removed subdirectory: {item_path}")
                        except Exception as sub_e:
                            log_warning(f"Could not remove {item_path}: {sub_e}")
                except Exception as clean_e:
                    log_warning(f"Could not clean directory contents: {clean_e}")
        
        # Create fresh directory
        log_info(f"Creating directory: {directory}")
        os.makedirs(directory, exist_ok=True)
        
        # Verify directory exists
        if os.path.exists(directory):
            log_info(f"Directory ready: {directory}")
            return True
        else:
            log_error(f"Failed to create directory: {directory}")
            return False
            
    except Exception as e:
        log_error(f"Error handling directory {directory}: {e}")
        return False

def clean_and_create_directory_structure():
    """Clean and create directory structure"""
    log_step("Preparing directory structure")
    
    # Process directories in order
    directories = [
        'data',
        'logs',
        'resources/company'
    ]
    
    # First ensure parent directories exist
    for directory in directories:
        parent = os.path.dirname(directory)
        if parent and not os.path.exists(parent):
            log_info(f"Creating parent directory: {parent}")
            os.makedirs(parent, exist_ok=True)
    
    # Then process each directory
    for directory in directories:
        if not ensure_directory(directory):
            raise Exception(f"Failed to prepare directory: {directory}")
        else:
            # Double check directory is usable
            try:
                # Try to create a test file
                test_file = os.path.join(directory, 'test.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.unlink(test_file)
                log_info(f"Verified directory is writable: {directory}")
            except Exception as e:
                log_error(f"Directory is not writable: {directory}")
                raise Exception(f"Directory {directory} is not writable: {e}")

def create_env_file(company_name: str, root_email: str, root_password: str, 
                   master_password: str, support_email: str, copyright_year: str) -> None:
    """Create .env file with required variables"""
    try:
        log_step("Creating .env file")
        
        env_content = f"""# Company Information
COMPANY_NAME="{company_name}"
COPYRIGHT_YEAR="{copyright_year}"
SUPPORT_EMAIL="{support_email}"

# Root Account
ROOT_EMAIL="{root_email}"
ROOT_PASSWORD="{root_password}"

# Security
MASTER_PASSWORD="{master_password}"

# File Paths
SALT_FILE="data/security/salt.key"
USERS_FILE="data/users/users.enc"
SCHEMA_FILE="data/database/schema.enc"
DATABASE_FILE="data/database/database.enc"
"""
        
        with open(".env", "w") as f:
            f.write(env_content.strip())
            
        log_info("Created .env file")
    except Exception as e:
        log_error(f"Failed to create .env file: {str(e)}")
        raise

def setup_resources():
    """Setup resources"""
    log_step("Setting up resources")
    
    print("\nResource Setup:")
    print("1. Please place your company logo (PNG format) in resources/company/logo.png")
    print("2. Please place your company icon (ICO format) in resources/company/icon.ico")
    
    # Copy dummy resources
    resource_files = {
        'resources/dummy-logo.png': 'resources/company/logo.png',
        'resources/dummy-logo.ico': 'resources/company/icon.ico'
    }
    
    for src, dest in resource_files.items():
        try:
            if not os.path.exists(dest):
                shutil.copy2(src, dest)
                log_info(f"Copied resource: {src} -> {dest}")
            else:
                log_info(f"Resource already exists: {dest}")
        except Exception as e:
            log_warning(f"Could not copy resource {src}: {e}")

def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """Basic password validation"""
    if len(password) < 8:
        print("Password must be at least 8 characters long")
        return False
    if not any(c.isupper() for c in password):
        print("Password must contain at least one uppercase letter")
        return False
    if not any(c.islower() for c in password):
        print("Password must contain at least one lowercase letter")
        return False
    if not any(c.isdigit() for c in password):
        print("Password must contain at least one number")
        return False
    return True

def get_validated_input(prompt: str, validation_func=None, is_password: bool = False) -> str:
    """Get and validate user input"""
    while True:
        if is_password:
            value = getpass(prompt)
        else:
            value = input(prompt)
        
        if validation_func is None or validation_func(value):
            return value
        print("Invalid input. Please try again.")

def initialize_user_database(root_email: str, root_password: str, master_password: str) -> None:
    """Initialize user database with root account"""
    try:
        log_step("Initializing user database")
        
        # Create security manager
        security_manager = SecurityManager(salt_file="data/security/salt.key")
        
        # Create user manager
        user_manager = UserManager(
            security_manager=security_manager,
            users_file="data/users/users.enc"
        )
        
        # Root account will be created automatically by UserManager
        log_info("Initialized user database with root account")
    except Exception as e:
        log_error(f"Failed to initialize user database: {str(e)}")
        raise

def main():
    print("=== Database Project Initialization ===")
    
    try:
        # Get company and root information with validation
        log_step("Collecting initialization information")
        company_name = get_validated_input("Enter company name: ")
        root_email = get_validated_input("Enter root email: ", validate_email)
        root_password = get_validated_input("Enter root password: ", validate_password, True)
        master_password = get_validated_input("Enter master password for database encryption: ", validate_password, True)
        copyright_year = get_validated_input("Enter copyright year: ")
        support_email = get_validated_input("Enter support email: ", validate_email)
        
        # Clean and create directory structure
        clean_and_create_directory_structure()
        
        # Create .env file with all required variables
        create_env_file(
            company_name=company_name,
            root_email=root_email,
            root_password=root_password,
            master_password=master_password,
            support_email=support_email,
            copyright_year=copyright_year
        )
        
        # Initialize user database with root account
        initialize_user_database(root_email, root_password, master_password)
        
        # Setup resources
        setup_resources()
        
        log_step("Initialization Complete!")
        print("\nNext steps:")
        print("1. Replace dummy logo and icon in resources/company/ with your company's assets")
        print("2. Review settings in .env file if needed")
        print("3. Run 'python src/main.py' to start the application")
        print("4. Log in with the root credentials you provided")
        print("5. Set up the database schema and additional users through the root interface")
        
    except Exception as e:
        log_error(f"Initialization failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInitialization cancelled.")
        sys.exit(1) 