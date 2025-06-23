import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QFile, QTextStream
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional

from core import SecurityManager, UserManager, DataManager
from ui import LoginWindow, MainWindow

def get_env_var(var_name: str) -> str:
    """Get environment variable with error handling"""
    value = os.getenv(var_name)
    if value is None:
        print(f"Error: Required environment variable {var_name} not found!")
        print("Please check your .env file")
        sys.exit(1)
    return value

def load_styles(app):
    """Load application styles from QSS file"""
    style_file = QFile("src/ui/styles.qss")
    if style_file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(style_file)
        app.setStyleSheet(stream.readAll())
        style_file.close()

def check_initialization():
    """Check if the project has been initialized"""
    required_files = [
        '.env',
        'resources/company/logo.png',
        'resources/company/icon.ico'
    ]
    
    required_dirs = [
        'data',
        'logs',
        'resources/company'
    ]
    
    # Check directories
    for directory in required_dirs:
        if not os.path.exists(directory):
            return False
            
    # Check files
    for file in required_files:
        if not os.path.exists(file):
            return False
            
    return True

def main():
    # Check initialization
    if not check_initialization():
        print("Error: Project not initialized!")
        print("Please run 'python src/initialize_project.py' first")
        sys.exit(1)
    
    # Load environment variables
    load_dotenv()
    
    # Create application
    app = QApplication(sys.argv)
    
    # Load styles
    load_styles(app)
    
    # Get required environment variables
    salt_file = get_env_var('SALT_FILE')
    users_file = get_env_var('USERS_FILE')
    schema_file = get_env_var('SCHEMA_FILE')
    data_file = get_env_var('DATABASE_FILE')
    
    # Initialize managers
    security_manager = SecurityManager(salt_file=salt_file)
    user_manager = UserManager(security_manager, users_file=users_file)
    data_manager = DataManager(
        security_manager,
        schema_file=schema_file,
        data_file=data_file
    )
    
    # Create login window
    global login_window, main_window
    login_window = LoginWindow(user_manager)
    main_window = None
    
    # Handle successful login
    def handle_login(token, user_data):
        # Create and show main window
        global main_window
        main_window = MainWindow(user_manager, data_manager, token, user_data)
        main_window.show()
        # Hide login window instead of letting it be destroyed
        login_window.hide()
    
    # Connect login signal
    login_window.login_successful.connect(handle_login)
    
    # Show login window
    login_window.show()
    
    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 