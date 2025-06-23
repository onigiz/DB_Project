from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QFileDialog, QMessageBox, QMenuBar, QMenu, QStatusBar,
                             QDialog, QLineEdit, QComboBox, QSpinBox, QGroupBox)
from PySide6.QtCore import Qt, Slot, Signal, QSize
from PySide6.QtGui import QAction, QIcon, QWindow
import os
import pandas as pd
from datetime import datetime

# Add Qt constants
from PySide6.QtCore import Qt
Qt.WA_TransparentForMouseEvents = Qt.WidgetAttribute.WA_TransparentForMouseEvents
Qt.WindowStaysOnTopHint = Qt.WindowType.WindowStaysOnTopHint

class SchemaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Define Schema")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Schema table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Column Name", "Excel Column", "Data Type"])
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Column")
        add_button.clicked.connect(self.add_row)
        remove_button = QPushButton("Remove Column")
        remove_button.clicked.connect(self.remove_row)
        save_button = QPushButton("Save Schema")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Add name field
        self.table.setItem(row, 0, QTableWidgetItem(""))
        
        # Add Excel column field
        self.table.setItem(row, 1, QTableWidgetItem(""))
        
        # Add data type combo box
        type_combo = QComboBox()
        type_combo.addItems(["string", "number", "date"])
        self.table.setCellWidget(row, 2, type_combo)
        
    def remove_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            
    def get_schema(self):
        schema = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            excel_col = self.table.item(row, 1).text().strip()
            data_type = self.table.cellWidget(row, 2).currentText()
            
            if name and excel_col:
                schema.append({
                    "name": name,
                    "excel_column": excel_col,
                    "data_type": data_type
                })
        return schema

class MainWindow(QMainWindow):
    # Signal emitted when logout is requested
    logout_requested = Signal()
    
    def __init__(self, user_manager, data_manager, user_token, user_data):
        super().__init__()
        self.user_manager = user_manager
        self.data_manager = data_manager
        self.user_token = user_token
        self.user_data = user_data
        self.current_page = 1
        self.page_size = 100
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        self.setWindowTitle('Data Management System')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create table
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Make table read-only for all users
        
        # Create navigation buttons
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.previous_page)
        nav_layout.addWidget(self.prev_button)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_page)
        nav_layout.addWidget(self.next_button)
        
        # Add edit buttons if user is admin, root or moderator
        if self.user_data['role'] in ['root', 'admin', 'moderator']:
            edit_layout = QHBoxLayout()
            
            add_button = QPushButton("Add Record")
            add_button.clicked.connect(self.show_add_record_dialog)
            edit_layout.addWidget(add_button)
            
            edit_button = QPushButton("Edit Record")
            edit_button.clicked.connect(self.show_edit_record_dialog)
            edit_layout.addWidget(edit_button)
            
            delete_button = QPushButton("Delete Record")
            delete_button.clicked.connect(self.delete_selected_record)
            edit_layout.addWidget(delete_button)
            
            layout.addLayout(edit_layout)
        
        layout.addLayout(nav_layout)
        layout.addWidget(self.table)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Load initial data
        self.load_data()
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        # Excel upload (admin/root/moderator only)
        if self.user_data['role'] in ['root', 'admin', 'moderator']:
            upload_action = QAction('Upload Excel', self)
            upload_action.triggered.connect(self.handle_excel_upload)
            file_menu.addAction(upload_action)
        
        # Schema definition (admin/root only)
        if self.user_data['role'] in ['root', 'admin']:
            schema_action = QAction('Define Schema', self)
            schema_action.triggered.connect(self.handle_schema_definition)
            file_menu.addAction(schema_action)
            
            # Database configuration (admin/root only)
            db_config_action = QAction('Database Configuration', self)
            db_config_action.triggered.connect(self.show_database_config)
            file_menu.addAction(db_config_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Admin menu (only for admin/root users)
        if self.user_data['role'] in ['root', 'admin']:
            admin_menu = menubar.addMenu('Admin')
            
            users_action = QAction('Manage Users', self)
            users_action.triggered.connect(self.show_user_management)
            admin_menu.addAction(users_action)
        
        # Account menu
        account_menu = menubar.addMenu('Account')
        
        change_password_action = QAction('Change Password', self)
        change_password_action.triggered.connect(self.show_change_password)
        account_menu.addAction(change_password_action)
        
        logout_action = QAction('Logout', self)
        logout_action.triggered.connect(self.handle_logout)
        account_menu.addAction(logout_action)

        # Create role label directly on the main window
        role_label = QLabel(f"• {self.user_data['role'].upper()}", self)
        role_label.setObjectName("roleLabel")
        
        # Set color based on role
        role_colors = {
            'root': '#0078d4',      # Mavi
            'admin': '#28a745',     # Yeşil
            'moderator': '#ffc107', # Sarı
            'user': '#6f42c1'       # Mor
        }
        
        role_color = role_colors.get(self.user_data['role'].lower(), '#6f42c1')  # Default to purple if role not found
        
        role_label.setStyleSheet(f"""
            QLabel {{
                color: {role_color};
                font-weight: bold;
                font-size: 14px;
                padding: 5px 10px;
                background: none;
                border: none;
            }}
        """)
        
        # Position the label in the top-right corner
        menubar_height = menubar.height()
        role_label.move(self.width() - role_label.width() - 10, 0)
        
        # Update label position when window is resized
        self.resizeEvent = lambda event: role_label.move(
            self.width() - role_label.width() - 10,
            0
        )
    
    def show_add_record_dialog(self):
        """Show dialog to add a new record"""
        if self.user_data['role'] not in ['root', 'admin', 'moderator']:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Record")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Get schema for fields
        schema = self.data_manager.get_schema()
        fields = {}
        
        for col_def in schema:
            field_layout = QHBoxLayout()
            label = QLabel(col_def["name"])
            field = QLineEdit()
            field_layout.addWidget(label)
            field_layout.addWidget(field)
            layout.addLayout(field_layout)
            fields[col_def["name"]] = field
        
        buttons = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        
        def handle_save():
            record_data = {name: field.text() for name, field in fields.items()}
            success, message = self.data_manager.add_record(self.user_token, record_data)
            if success:
                QMessageBox.information(dialog, "Success", message)
                dialog.accept()
                self.load_data()
            else:
                QMessageBox.warning(dialog, "Error", message)
        
        save.clicked.connect(handle_save)
        cancel.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def show_edit_record_dialog(self):
        """Show dialog to edit selected record"""
        if self.user_data['role'] not in ['root', 'admin', 'moderator']:
            return
            
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Please select a record to edit")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Record")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Get schema and current data
        schema = self.data_manager.get_schema()
        fields = {}
        
        for col_idx, col_def in enumerate(schema):
            field_layout = QHBoxLayout()
            label = QLabel(col_def["name"])
            field = QLineEdit()
            current_value = self.table.item(current_row, col_idx).text()
            field.setText(current_value)
            field_layout.addWidget(label)
            field_layout.addWidget(field)
            layout.addLayout(field_layout)
            fields[col_def["name"]] = field
        
        buttons = QHBoxLayout()
        save = QPushButton("Save")
        cancel = QPushButton("Cancel")
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        
        def handle_save():
            record_data = {name: field.text() for name, field in fields.items()}
            success, message = self.data_manager.update_record(
                self.user_token,
                (self.current_page - 1) * self.page_size + current_row,
                record_data
            )
            if success:
                QMessageBox.information(dialog, "Success", message)
                dialog.accept()
                self.load_data()
            else:
                QMessageBox.warning(dialog, "Error", message)
        
        save.clicked.connect(handle_save)
        cancel.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def delete_selected_record(self):
        """Delete selected record"""
        if self.user_data['role'] not in ['root', 'admin', 'moderator']:
            return
            
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Error", "Please select a record to delete")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this record?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, message = self.data_manager.delete_record(
                self.user_token,
                (self.current_page - 1) * self.page_size + current_row
            )
            if success:
                QMessageBox.information(self, "Success", message)
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def handle_excel_upload(self):
        """Handle Excel file upload"""
        if self.user_data['role'] not in ['root', 'admin', 'moderator']:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Excel File",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            success, message = self.data_manager.process_excel(self.user_token, file_path)
            if success:
                QMessageBox.information(self, "Success", message)
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", message)
    
    def handle_schema_definition(self):
        """Handle schema definition"""
        if self.user_data['role'] not in ['root', 'admin']:
            return
            
        dialog = SchemaDialog(self)
        
        # Load existing schema
        existing_schema = self.data_manager.get_schema()
        if existing_schema:
            for column in existing_schema:
                dialog.table.insertRow(dialog.table.rowCount())
                row = dialog.table.rowCount() - 1
                dialog.table.setItem(row, 0, QTableWidgetItem(column["name"]))
                dialog.table.setItem(row, 1, QTableWidgetItem(column["excel_column"]))
                type_combo = dialog.table.cellWidget(row, 2)
                type_combo.setCurrentText(column["data_type"])
        
        if dialog.exec() == QDialog.Accepted:
            schema = dialog.get_schema()
            if schema:
                if self.data_manager.update_schema(self.user_token, schema):
                    QMessageBox.information(
                        self,
                        "Success",
                        "Schema updated successfully"
                    )
                    self.load_data()
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Failed to update schema"
                    )
    
    def show_user_management(self):
        """Show user management dialog (admin/root only)"""
        if self.user_data['role'] not in ['root', 'admin']:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("User Management")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        # User table
        user_table = QTableWidget()
        user_table.setColumnCount(4)
        user_table.setHorizontalHeaderLabels(["Email", "Role", "Created", "Last Login"])
        layout.addWidget(user_table)
        
        # Load users
        users = self.user_manager.get_users(self.user_token)
        if users:
            user_table.setRowCount(len(users))
            for row, user in enumerate(users):
                user_table.setItem(row, 0, QTableWidgetItem(user["email"]))
                user_table.setItem(row, 1, QTableWidgetItem(user["role"]))
                user_table.setItem(row, 2, QTableWidgetItem(user["created_at"]))
                user_table.setItem(row, 3, QTableWidgetItem(user["last_login"] or "Never"))
        
        # Buttons
        buttons = QHBoxLayout()
        
        add_user = QPushButton("Add User")
        delete_user = QPushButton("Delete User")
        reset_password = QPushButton("Reset Password")
        close_button = QPushButton("Close")
        
        buttons.addWidget(add_user)
        buttons.addWidget(delete_user)
        buttons.addWidget(reset_password)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)
        
        def handle_add_user():
            # Show add user dialog
            add_dialog = QDialog(dialog)
            add_dialog.setWindowTitle("Add User")
            add_dialog.setModal(True)
            
            add_layout = QVBoxLayout(add_dialog)
            
            email = QLineEdit()
            email.setPlaceholderText("Email")
            add_layout.addWidget(email)
            
            password = QLineEdit()
            password.setEchoMode(QLineEdit.Password)
            password.setPlaceholderText("Password")
            add_layout.addWidget(password)
            
            role = QComboBox()
            # Root can create any role, admin can only create moderator and user roles
            if self.user_data['role'] == 'root':
                role.addItems(["user", "moderator", "admin"])
            else:  # admin
                role.addItems(["user", "moderator"])
            add_layout.addWidget(role)
            
            add_buttons = QHBoxLayout()
            save = QPushButton("Save")
            cancel = QPushButton("Cancel")
            add_buttons.addWidget(save)
            add_buttons.addWidget(cancel)
            add_layout.addLayout(add_buttons)
            
            def handle_save():
                if self.user_manager.create_user(
                    self.user_token,
                    email.text(),
                    password.text(),
                    role.currentText()
                ):
                    QMessageBox.information(
                        add_dialog,
                        "Success",
                        "User created successfully"
                    )
                    add_dialog.accept()
                    # Refresh user table
                    dialog.accept()
                    self.show_user_management()
                else:
                    QMessageBox.warning(
                        add_dialog,
                        "Error",
                        "Failed to create user"
                    )
            
            save.clicked.connect(handle_save)
            cancel.clicked.connect(add_dialog.reject)
            
            add_dialog.exec()
        
        def handle_delete_user():
            current_row = user_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(dialog, "Error", "Please select a user to delete")
                return
            
            user_email = user_table.item(current_row, 0).text()
            user_role = user_table.item(current_row, 1).text()
            
            # Check permissions based on roles
            if self.user_data['role'] == 'admin':
                if user_role in ['root', 'admin']:
                    QMessageBox.warning(dialog, "Error", "You don't have permission to delete this user")
                    return
            
            if user_email == self.user_data["email"]:
                QMessageBox.warning(dialog, "Error", "Cannot delete your own account")
                return
            
            reply = QMessageBox.question(
                dialog,
                "Confirm Delete",
                f"Are you sure you want to delete user {user_email}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.user_manager.delete_user(self.user_token, user_email):
                    QMessageBox.information(
                        dialog,
                        "Success",
                        "User deleted successfully"
                    )
                    dialog.accept()
                    self.show_user_management()
                else:
                    QMessageBox.warning(
                        dialog,
                        "Error",
                        "Failed to delete user"
                    )
        
        def handle_reset_password():
            current_row = user_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(dialog, "Error", "Please select a user")
                return
            
            user_email = user_table.item(current_row, 0).text()
            user_role = user_table.item(current_row, 1).text()
            
            # Check permissions based on roles
            if self.user_data['role'] == 'admin':
                if user_role in ['root', 'admin']:
                    QMessageBox.warning(dialog, "Error", "You don't have permission to reset this user's password")
                    return
            
            # Show reset password dialog
            reset_dialog = QDialog(dialog)
            reset_dialog.setWindowTitle("Reset Password")
            reset_dialog.setModal(True)
            
            reset_layout = QVBoxLayout(reset_dialog)
            
            new_password = QLineEdit()
            new_password.setEchoMode(QLineEdit.Password)
            new_password.setPlaceholderText("New Password")
            reset_layout.addWidget(new_password)
            
            confirm_password = QLineEdit()
            confirm_password.setEchoMode(QLineEdit.Password)
            confirm_password.setPlaceholderText("Confirm Password")
            reset_layout.addWidget(confirm_password)
            
            reset_buttons = QHBoxLayout()
            save = QPushButton("Save")
            cancel = QPushButton("Cancel")
            reset_buttons.addWidget(save)
            reset_buttons.addWidget(cancel)
            reset_layout.addLayout(reset_buttons)
            
            def handle_save():
                if new_password.text() != confirm_password.text():
                    QMessageBox.warning(
                        reset_dialog,
                        "Error",
                        "Passwords do not match"
                    )
                    return
                
                if self.user_manager.reset_password(
                    self.user_token,
                    user_email,
                    new_password.text()
                ):
                    QMessageBox.information(
                        reset_dialog,
                        "Success",
                        "Password reset successfully"
                    )
                    reset_dialog.accept()
                else:
                    QMessageBox.warning(
                        reset_dialog,
                        "Error",
                        "Failed to reset password"
                    )
            
            save.clicked.connect(handle_save)
            cancel.clicked.connect(reset_dialog.reject)
            
            reset_dialog.exec()
        
        add_user.clicked.connect(handle_add_user)
        delete_user.clicked.connect(handle_delete_user)
        reset_password.clicked.connect(handle_reset_password)
        close_button.clicked.connect(dialog.accept)
        
        dialog.exec()
    
    def load_data(self):
        """Load data into the table"""
        result = self.data_manager.get_data(self.current_page, self.page_size)
        data = result["data"]
        metadata = result["metadata"]
        pagination = result["pagination"]
        
        if not data:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.status_bar.showMessage("No data available")
            return
        
        # Get schema for headers
        schema = self.data_manager.get_schema()
        headers = [col["name"] for col in schema]
        
        # Set up table
        self.table.setRowCount(len(data))
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # Fill data
        for row, record in enumerate(data):
            for col, header in enumerate(headers):
                value = record.get(header, "")
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        
        # Update status bar
        self.status_bar.showMessage(
            f"Showing {len(data)} records (Page {pagination['current_page']} of {pagination['total_pages']})"
        )
        
        # Update navigation buttons
        self.prev_button.setEnabled(pagination['current_page'] > 1)
        self.next_button.setEnabled(pagination['current_page'] < pagination['total_pages'])
    
    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_data()
    
    def next_page(self):
        """Go to next page"""
        self.current_page += 1
        self.load_data()
    
    def handle_logout(self):
        """Handle user logout"""
        self.logout_requested.emit()
        self.close()
        
    def show_change_password(self):
        """Show dialog to change password"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Password")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Create input fields
        current_password = QLineEdit()
        current_password.setPlaceholderText("Current Password")
        current_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(current_password)
        
        new_password = QLineEdit()
        new_password.setPlaceholderText("New Password")
        new_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(new_password)
        
        confirm_password = QLineEdit()
        confirm_password.setPlaceholderText("Confirm New Password")
        confirm_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(confirm_password)
        
        # Create buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        def handle_save():
            if new_password.text() != confirm_password.text():
                QMessageBox.warning(dialog, "Error", "New passwords do not match!")
                return
                
            success = self.user_manager.change_password(
                self.user_token,
                current_password.text(),
                new_password.text()
            )
            
            if success:
                QMessageBox.information(dialog, "Success", "Password changed successfully!")
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Error", "Failed to change password. Please check your current password.")
        
        save_button.clicked.connect(handle_save)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()
    
    def show_database_config(self):
        """Show dialog to configure database location and password"""
        if self.user_data['role'] not in ['root', 'admin']:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Database Configuration")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # Directory selection
        dir_group = QGroupBox("Database Location")
        dir_layout = QHBoxLayout()
        
        dir_path = QLineEdit()
        dir_path.setReadOnly(True)
        dir_layout.addWidget(dir_path)
        
        browse_button = QPushButton("Browse...")
        def browse_directory():
            directory = QFileDialog.getExistingDirectory(dialog, "Select Database Directory")
            if directory:
                dir_path.setText(directory)
        browse_button.clicked.connect(browse_directory)
        dir_layout.addWidget(browse_button)
        
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # Password fields
        pass_group = QGroupBox("Database Password")
        pass_layout = QVBoxLayout()
        
        new_password = QLineEdit()
        new_password.setPlaceholderText("New Database Password")
        new_password.setEchoMode(QLineEdit.Password)
        pass_layout.addWidget(new_password)
        
        confirm_password = QLineEdit()
        confirm_password.setPlaceholderText("Confirm Database Password")
        confirm_password.setEchoMode(QLineEdit.Password)
        pass_layout.addWidget(confirm_password)
        
        pass_group.setLayout(pass_layout)
        layout.addWidget(pass_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        def handle_save():
            if not dir_path.text():
                QMessageBox.warning(dialog, "Error", "Please select a database directory!")
                return
                
            if new_password.text() != confirm_password.text():
                QMessageBox.warning(dialog, "Error", "Passwords do not match!")
                return
                
            if not new_password.text():
                QMessageBox.warning(dialog, "Error", "Please enter a database password!")
                return
                
            success, message = self.data_manager.update_database_config(
                self.user_token,
                dir_path.text(),
                new_password.text()
            )
            
            if success:
                QMessageBox.information(dialog, "Success", message)
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Error", message)
        
        save_button.clicked.connect(handle_save)
        cancel_button.clicked.connect(dialog.reject)
        
        dialog.exec()