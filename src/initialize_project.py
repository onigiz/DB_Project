#!/usr/bin/env python3
import os
import sys
import shutil
from getpass import getpass
import json
from pathlib import Path

def create_directory_structure():
    """Create necessary directories"""
    directories = [
        'data',
        'logs',
        'resources/company'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {directory}")

def create_env_file(company_name, admin_email):
    """Create .env file with initial configuration"""
    env_content = f"""# Database Configuration
MASTER_PASSWORD={getpass('Enter master password for database encryption: ')}

# Security Settings
SESSION_DURATION_HOURS=24
MIN_PASSWORD_LENGTH=8
SALT_FILE=data/salt.key

# File Locations
USERS_FILE=data/users.enc
DATABASE_FILE=data/database.enc
SCHEMA_FILE=data/schema.enc
CONFIG_FILE=data/db_config.enc

# Company Information
COMPANY_NAME={company_name}
COPYRIGHT_YEAR={input('Enter copyright year: ')}
SUPPORT_EMAIL={input('Enter support email: ')}

# Initial Admin Account
ADMIN_EMAIL={admin_email}
ADMIN_PASSWORD={getpass('Enter admin password: ')}
"""
    with open('.env', 'w') as f:
        f.write(env_content)
    print("Created .env file with initial configuration")

def setup_resources():
    """Guide through resource setup"""
    print("\nResource Setup:")
    print("1. Please place your company logo (PNG format) in resources/company/logo.png")
    print("2. Please place your company icon (ICO format) in resources/company/icon.ico")
    
    # Copy dummy resources if company resources don't exist
    if not os.path.exists('resources/company/logo.png'):
        shutil.copy('resources/dummy-logo.png', 'resources/company/logo.png')
        print("Copied dummy logo - please replace with company logo")
    
    if not os.path.exists('resources/company/icon.ico'):
        shutil.copy('resources/dummy-logo.ico', 'resources/company/icon.ico')
        print("Copied dummy icon - please replace with company icon")

def main():
    print("=== Database Project Initialization ===")
    
    # Get company information
    company_name = input("Enter company name: ")
    admin_email = input("Enter admin email: ")
    
    # Create directory structure
    create_directory_structure()
    
    # Create .env file
    create_env_file(company_name, admin_email)
    
    # Setup resources
    setup_resources()
    
    print("\nInitialization Complete!")
    print("\nNext steps:")
    print("1. Replace dummy logo and icon in resources/company/ with your company's assets")
    print("2. Review and adjust settings in .env file if needed")
    print("3. Run 'python src/main.py' to start the application")
    print("4. Log in with the admin credentials you provided")
    print("5. Set up the database schema and additional users through the admin interface")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInitialization cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during initialization: {e}")
        sys.exit(1) 