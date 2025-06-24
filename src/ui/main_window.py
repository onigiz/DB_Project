from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QFileDialog, QMessageBox, QMenuBar, QMenu, QStatusBar,
                             QDialog, QLineEdit, QComboBox, QSpinBox, QGroupBox,
                             QHeaderView, QDateEdit)
from PySide6.QtCore import Qt, Slot, Signal, QSize, QDate
from PySide6.QtGui import QAction, QIcon, QWindow, QColor
import os
import pandas as pd
from datetime import datetime
import json

# Add Qt constants
from PySide6.QtCore import Qt
Qt.WA_TransparentForMouseEvents = Qt.WidgetAttribute.WA_TransparentForMouseEvents
Qt.WindowStaysOnTopHint = Qt.WindowType.WindowStaysOnTopHint

class SchemaDialog(QDialog):
    def __init__(self, parent=None, existing_schema=None):
        super().__init__(parent)
        self.setWindowTitle("Define Schema")
        self.setModal(True)
        self.existing_schema = existing_schema
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Schema name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Schema Name:")
        self.name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Schema table
        self.table = QTableWidget(0, 4)  # Added nullable column
        self.table.setHorizontalHeaderLabels(["Column Name", "Excel Column", "Data Type", "Nullable"])
        layout.addWidget(self.table)
        
        # Load existing schema if provided
        if self.existing_schema:
            self.load_existing_schema()
        
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
        
    def load_existing_schema(self):
        """Load existing schema into the dialog"""
        if not self.existing_schema:
            return
            
        self.name_input.setText(self.existing_schema.get("metadata", {}).get("name", ""))
        
        for column in self.existing_schema.get("columns", []):
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Set column name
            self.table.setItem(row, 0, QTableWidgetItem(column["name"]))
            
            # Set Excel column
            self.table.setItem(row, 1, QTableWidgetItem(column["excel_column"]))
            
            # Set data type
            type_combo = QComboBox()
            type_combo.addItems(["TEXT", "NUMBER"])
            type_combo.setCurrentText(column["type"])
            self.table.setCellWidget(row, 2, type_combo)
            
            # Set nullable checkbox
            nullable_check = QTableWidgetItem()
            nullable_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            nullable_check.setCheckState(Qt.CheckState.Checked if column.get("nullable", False) else Qt.CheckState.Unchecked)
            self.table.setItem(row, 3, nullable_check)
        
    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Add name field
        self.table.setItem(row, 0, QTableWidgetItem(""))
        
        # Add Excel column field
        self.table.setItem(row, 1, QTableWidgetItem(""))
        
        # Add data type combo box
        type_combo = QComboBox()
        type_combo.addItems(["TEXT", "NUMBER"])
        self.table.setCellWidget(row, 2, type_combo)
        
        # Add nullable checkbox
        nullable_check = QTableWidgetItem()
        nullable_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        nullable_check.setCheckState(Qt.CheckState.Unchecked)
        self.table.setItem(row, 3, nullable_check)
        
    def remove_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)
            
    def get_schema_name(self):
        """Get the schema name"""
        return self.name_input.text().strip()
            
    def get_schema(self):
        """Get the schema definition"""
        schema = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            excel_col = self.table.item(row, 1).text().strip()
            data_type = self.table.cellWidget(row, 2).currentText()
            nullable = self.table.item(row, 3).checkState() == Qt.CheckState.Checked
            
            if name and excel_col:
                schema.append({
                    "name": name,
                    "excel_column": excel_col,
                    "type": data_type,
                    "nullable": nullable
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
        
        # Validate and set user_data
        if not isinstance(user_data, dict):
            print(f"WARNING: user_data is not a dictionary: {user_data}")
            self.user_data = {}
        else:
            self.user_data = user_data.copy()  # Make a copy to avoid reference issues
            
        # Ensure required fields exist
        if 'email' not in self.user_data or 'role' not in self.user_data:
            print(f"WARNING: user_data missing required fields: {self.user_data}")
            # Get user info from token
            token_data = self.user_manager.security_manager.verify_session_token(user_token)
            if token_data and isinstance(token_data, dict):
                self.user_data.update({
                    'email': token_data.get('email', ''),
                    'role': token_data.get('role', '')
                })
            else:
                print("ERROR: Could not get user info from token")
        
        print(f"Initialized MainWindow with user_data: {self.user_data}")
        
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
        try:
            # Get active schema
            active_schema = self.data_manager.schema_manager.get_active_schema(self.user_token)
            if not active_schema:
                QMessageBox.warning(self, "Warning", "Please define and set an active schema first")
                return
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Record")
            dialog.setModal(True)
            
            # Create layout
            layout = QVBoxLayout(dialog)
            
            # Create form
            form_layout = QVBoxLayout()
            fields = {}
            
            for column in active_schema["columns"]:
                field_layout = QHBoxLayout()
                
                # Label
                label = QLabel(f"{column['name']}:")
                field_layout.addWidget(label)
                
                # Input field
                if column["type"] == "NUMBER":
                    field = QLineEdit()
                    field.setPlaceholderText("Enter a number")
                else:
                    field = QLineEdit()
                    field.setPlaceholderText(f"Enter {column['name']}")
                
                field_layout.addWidget(field)
                form_layout.addLayout(field_layout)
                fields[column["name"]] = field
            
            layout.addLayout(form_layout)
            
            # Add buttons
            button_layout = QHBoxLayout()
            save_button = QPushButton("Save")
            save_button.clicked.connect(handle_save)
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(dialog.reject)
            
            button_layout.addWidget(save_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            def handle_save():
                """Handle saving the new record"""
                record = {}
                
                # Collect values
                for column in active_schema["columns"]:
                    value = fields[column["name"]].text().strip()
                    
                    # Handle empty values
                    if not value:
                        if not column.get("nullable", False):
                            QMessageBox.warning(
                                dialog,
                                "Error",
                                f"Field {column['name']} cannot be empty"
                            )
                            return
                        record[column["name"]] = None
                        continue
                    
                    # Convert number fields
                    if column["type"] == "NUMBER":
                        try:
                            record[column["name"]] = float(value)
                        except ValueError:
                            QMessageBox.warning(
                                dialog,
                                "Error",
                                f"Field {column['name']} must be a number"
                            )
                            return
                    else:
                        record[column["name"]] = value
                
                # Add record
                success, message = self.data_manager.add_record(self.user_token, record)
                
                if success:
                    dialog.accept()
                    self.load_data()
                else:
                    QMessageBox.warning(dialog, "Error", message)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def show_edit_record_dialog(self):
        """Show dialog to edit a record"""
        try:
            # Get active schema
            active_schema = self.data_manager.schema_manager.get_active_schema(self.user_token)
            if not active_schema:
                QMessageBox.warning(self, "Warning", "Please define and set an active schema first")
                return
            
            # Get selected row
            current_row = self.table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Please select a record to edit")
                return
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Record")
            dialog.setModal(True)
            
            # Create layout
            layout = QVBoxLayout(dialog)
            
            # Create form
            form_layout = QVBoxLayout()
            fields = {}
            
            for column in active_schema["columns"]:
                field_layout = QHBoxLayout()
                
                # Label
                label = QLabel(f"{column['name']}:")
                field_layout.addWidget(label)
                
                # Input field
                if column["type"] == "NUMBER":
                    field = QLineEdit()
                    field.setPlaceholderText("Enter a number")
                else:
                    field = QLineEdit()
                    field.setPlaceholderText(f"Enter {column['name']}")
                
                # Set current value
                current_value = self.table.item(current_row, list(fields.keys()).index(column["name"]) if fields else 0)
                if current_value:
                    field.setText(current_value.text())
                
                field_layout.addWidget(field)
                form_layout.addLayout(field_layout)
                fields[column["name"]] = field
            
            layout.addLayout(form_layout)
            
            # Add buttons
            button_layout = QHBoxLayout()
            save_button = QPushButton("Save")
            save_button.clicked.connect(handle_save)
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(dialog.reject)
            
            button_layout.addWidget(save_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)
            
            def handle_save():
                """Handle saving the edited record"""
                record = {}
                
                # Collect values
                for column in active_schema["columns"]:
                    value = fields[column["name"]].text().strip()
                    
                    # Handle empty values
                    if not value:
                        if not column.get("nullable", False):
                            QMessageBox.warning(
                                dialog,
                                "Error",
                                f"Field {column['name']} cannot be empty"
                            )
                            return
                        record[column["name"]] = None
                        continue
                    
                    # Convert number fields
                    if column["type"] == "NUMBER":
                        try:
                            record[column["name"]] = float(value)
                        except ValueError:
                            QMessageBox.warning(
                                dialog,
                                "Error",
                                f"Field {column['name']} must be a number"
                            )
                            return
                    else:
                        record[column["name"]] = value
                
                # Update record
                success, message = self.data_manager.update_record(self.user_token, current_row, record)
                
                if success:
                    dialog.accept()
                    self.load_data()
                else:
                    QMessageBox.warning(dialog, "Error", message)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def delete_selected_record(self):
        """Delete selected record"""
        try:
            # Get active schema
            active_schema = self.data_manager.schema_manager.get_active_schema(self.user_token)
            if not active_schema:
                QMessageBox.warning(self, "Warning", "Please define and set an active schema first")
                return
            
            # Get selected row
            current_row = self.table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Warning", "Please select a record to delete")
                return
            
            # Confirm deletion
            confirm = QMessageBox.question(
                self,
                "Confirm Delete",
                "Are you sure you want to delete this record?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                success, message = self.data_manager.delete_record(self.user_token, current_row)
                
                if success:
                    self.load_data()
                else:
                    QMessageBox.warning(self, "Error", message)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def handle_excel_upload(self):
        """Handle Excel file upload"""
        try:
            # Check if there's an active schema
            active_schema = self.data_manager.schema_manager.get_active_schema(self.user_token)
            if not active_schema:
                QMessageBox.warning(self, "Warning", "Please define and set an active schema first")
                return
            
            # Get Excel file
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "Select Excel File",
                "",
                "Excel Files (*.xlsx *.xls)"
            )
            
            if file_name:
                # Process Excel file
                success, message = self.data_manager.process_excel(self.user_token, file_name)
                
                if success:
                    QMessageBox.information(self, "Success", message)
                    self.load_data()  # Reload data
                else:
                    QMessageBox.warning(self, "Error", f"Failed to process Excel file: {message}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def handle_schema_definition(self):
        """Handle schema definition"""
        try:
            # Get list of existing schemas
            schemas = self.data_manager.schema_manager.list_schemas(self.user_token)
            
            # Create schema selection dialog
            schema_select = QDialog(self)
            schema_select.setWindowTitle("Schema Management")
            schema_select.setModal(True)
            
            layout = QVBoxLayout(schema_select)
            
            # Add schema list
            schema_list = QComboBox()
            schema_list.addItem("-- Create New Schema --")
            for schema in schemas:
                schema_list.addItem(schema["name"])
            layout.addWidget(schema_list)
            
            # Add buttons
            button_layout = QHBoxLayout()
            
            edit_button = QPushButton("Edit/View Schema")
            edit_button.clicked.connect(lambda: handle_edit_schema(schema_list.currentText()))
            button_layout.addWidget(edit_button)
            
            set_active_button = QPushButton("Set as Active")
            set_active_button.clicked.connect(lambda: handle_set_active(schema_list.currentText()))
            button_layout.addWidget(set_active_button)
            
            new_button = QPushButton("Create New")
            new_button.clicked.connect(lambda: handle_new_schema())
            button_layout.addWidget(new_button)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(schema_select.close)
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            def handle_edit_schema(schema_name):
                """Handle editing an existing schema"""
                if schema_name == "-- Create New Schema --":
                    handle_new_schema()
                    return
                
                # Get existing schema
                schema_data = self.data_manager.schema_manager.get_schema(self.user_token, schema_name)
                if not schema_data:
                    QMessageBox.warning(self, "Error", "Could not load schema")
                    return
                
                # Show schema dialog with existing data
                dialog = SchemaDialog(self, schema_data)
                if dialog.exec():
                    # Get updated schema
                    new_schema = dialog.get_schema()
                    schema_name = dialog.get_schema_name()
                    
                    # Update schema
                    success, message = self.data_manager.schema_manager.create_schema(
                        self.user_token,
                        schema_name,
                        new_schema
                    )
                    
                    if success:
                        QMessageBox.information(self, "Success", "Schema updated successfully")
                        schema_select.close()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to update schema: {message}")
            
            def handle_set_active(schema_name):
                """Handle setting a schema as active"""
                if schema_name == "-- Create New Schema --":
                    QMessageBox.warning(self, "Error", "Please select a valid schema")
                    return
                
                # Set schema as active
                success, message = self.data_manager.schema_manager.set_active_schema(
                    self.user_token,
                    schema_name
                )
                
                if success:
                    QMessageBox.information(self, "Success", "Active schema updated successfully")
                    schema_select.close()
                    # Reload data with new schema
                    self.load_data()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to set active schema: {message}")
            
            def handle_new_schema():
                """Handle creating a new schema"""
                dialog = SchemaDialog(self)
                if dialog.exec():
                    # Get schema definition
                    schema = dialog.get_schema()
                    schema_name = dialog.get_schema_name()
                    
                    if not schema_name:
                        QMessageBox.warning(self, "Error", "Please provide a schema name")
                        return
                    
                    # Create new schema
                    success, message = self.data_manager.schema_manager.create_schema(
                        self.user_token,
                        schema_name,
                        schema
                    )
                    
                    if success:
                        QMessageBox.information(self, "Success", "Schema created successfully")
                        schema_select.close()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to create schema: {message}")
            
            schema_select.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
    
    def show_user_management(self):
        """Show user management dialog (admin/root only)"""
        if self.user_data['role'] not in ['root', 'admin']:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("User Management")
        dialog.setModal(True)
        dialog.resize(800, 600)  # Default size
        
        # Add maximize/fullscreen button
        dialog.setWindowFlags(
            dialog.windowFlags() |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        
        main_layout = QVBoxLayout(dialog)
        
        # Add filter section
        filter_layout = QHBoxLayout()
        
        # Email filter
        email_filter = QLineEdit()
        email_filter.setPlaceholderText("Filter by Email...")
        filter_layout.addWidget(email_filter)
        
        # Role filter
        role_filter = QComboBox()
        role_filter.addItems(["All Roles", "root", "admin", "moderator", "user"])
        filter_layout.addWidget(role_filter)
        
        # Date range filter for Created
        date_filter_layout = QHBoxLayout()
        date_from = QDateEdit()
        date_from.setCalendarPopup(True)
        date_to = QDateEdit()
        date_to.setCalendarPopup(True)
        date_from.setDate(QDate.currentDate().addYears(-1))  # Default to last year
        date_to.setDate(QDate.currentDate())  # Default to today
        
        date_filter_layout.addWidget(QLabel("Created From:"))
        date_filter_layout.addWidget(date_from)
        date_filter_layout.addWidget(QLabel("To:"))
        date_filter_layout.addWidget(date_to)
        filter_layout.addLayout(date_filter_layout)
        
        # Clear filters button
        clear_filters = QPushButton("Clear Filters")
        filter_layout.addWidget(clear_filters)
        
        main_layout.addLayout(filter_layout)
        
        # User table
        user_table = QTableWidget()
        user_table.setColumnCount(5)
        user_table.setHorizontalHeaderLabels([
            "Email",
            "Account Type: Current Type",
            "Change Account Type",
            "Created",
            "Last Login"
        ])
        user_table.setSortingEnabled(True)  # Enable sorting
        
        # Load users first to calculate column widths
        users = self.user_manager.get_users(self.user_token)
        all_users = users.copy() if users else []  # Keep a copy of all users for filtering
        
        def apply_filters():
            if not all_users:
                return
                
            filtered_users = all_users.copy()
            
            # Apply email filter
            if email_filter.text():
                filtered_users = [
                    user for user in filtered_users
                    if email_filter.text().lower() in user["email"].lower()
                ]
            
            # Apply role filter
            if role_filter.currentText() != "All Roles":
                filtered_users = [
                    user for user in filtered_users
                    if user["role"] == role_filter.currentText()
                ]
            
            # Apply date filter
            from_date = date_from.date().toPython()
            to_date = date_to.date().toPython()
            filtered_users = [
                user for user in filtered_users
                if from_date <= datetime.fromisoformat(user["created_at"]).date() <= to_date
            ]
            
            # Update table with filtered users
            user_table.setRowCount(len(filtered_users))
            for row, user in enumerate(filtered_users):
                # Email
                email_item = QTableWidgetItem(user["email"])
                if not user.get("can_modify", False):
                    email_item.setForeground(QColor("#FF0000"))
                user_table.setItem(row, 0, email_item)
                
                # Current Role (Account Type)
                current_role_item = QTableWidgetItem(user["role"].upper())
                if not user.get("can_modify", False):
                    current_role_item.setForeground(QColor("#FF0000"))
                user_table.setItem(row, 1, current_role_item)
                
                # Role ComboBox (Change Account Type)
                role_combo = QComboBox()
                if self.user_data['role'] == 'root':
                    role_combo.addItems(["root", "admin", "moderator", "user"])
                elif self.user_data['role'] == 'admin':
                    role_combo.addItems(["moderator", "user"])
                
                role_combo.setCurrentText(user["role"])
                role_combo.setEnabled(user.get("can_modify", False))
                
                if not user.get("can_modify", False):
                    role_combo.setStyleSheet("""
                        QComboBox:disabled {
                            color: #A0A0A0;
                            background-color: #F0F0F0;
                            border: 1px solid #D0D0D0;
                        }
                    """)
                
                def handle_role_change(email, new_role):
                    reply = QMessageBox.question(
                        dialog,
                        "Confirm Role Change",
                        f"Are you sure you want to change the role of {email} to {new_role}?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        success = self.user_manager.change_user_role(self.user_token, email, new_role)
                        if success:
                            QMessageBox.information(dialog, "Success", "Role updated successfully")
                            dialog.accept()
                            self.show_user_management()
                        else:
                            QMessageBox.warning(dialog, "Error", "Failed to update role")
                            role_combo.setCurrentText(user["role"])
                
                role_combo.currentTextChanged.connect(
                    lambda new_role, email=user["email"]: handle_role_change(email, new_role)
                )
                
                user_table.setCellWidget(row, 2, role_combo)
                
                # Created date
                created_item = QTableWidgetItem(user["created_at"])
                if not user.get("can_modify", False):
                    created_item.setForeground(QColor("#FF0000"))
                user_table.setItem(row, 3, created_item)
                
                # Last login
                last_login_item = QTableWidgetItem(user["last_login"] or "Never")
                if not user.get("can_modify", False):
                    last_login_item.setForeground(QColor("#FF0000"))
                user_table.setItem(row, 4, last_login_item)
        
        # Connect filter signals
        email_filter.textChanged.connect(apply_filters)
        role_filter.currentTextChanged.connect(apply_filters)
        date_from.dateChanged.connect(apply_filters)
        date_to.dateChanged.connect(apply_filters)
        
        def clear_all_filters():
            email_filter.clear()
            role_filter.setCurrentText("All Roles")
            date_from.setDate(QDate.currentDate().addYears(-1))
            date_to.setDate(QDate.currentDate())
        
        clear_filters.clicked.connect(clear_all_filters)
        
        # Initial population of table
        apply_filters()
        
        # Set column resize modes and adjust widths after populating data
        header = user_table.horizontalHeader()
        
        # Temporarily set all columns to ResizeToContents to calculate optimal widths
        for col in range(user_table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        
        # Get the calculated widths
        column_widths = [header.sectionSize(col) for col in range(user_table.columnCount())]
        
        # Set fixed widths based on content
        for col in range(user_table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(col, column_widths[col] + 20)
        
        # Make the email column stretch if there's extra space
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        
        main_layout.addWidget(user_table)
        
        # Buttons
        buttons = QHBoxLayout()
        
        add_user = QPushButton("Add User")
        delete_user = QPushButton("Delete User")
        reset_password = QPushButton("Reset Password")
        export_button = QPushButton("Export Data")
        
        # Style the export button with red background and white text
        export_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
        
        buttons.addWidget(add_user)
        buttons.addWidget(delete_user)
        buttons.addWidget(reset_password)
        buttons.addWidget(export_button)
        main_layout.addLayout(buttons)
        
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
            # Root can create any role except root, admin can only create moderator and user roles
            if self.user_data['role'] == 'root':
                role.addItems(["admin", "moderator", "user"])
            else:  # admin
                role.addItems(["moderator", "user"])
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
            """Handle user deletion with proper role-based permissions"""
            print("\n=== Starting handle_delete_user in MainWindow ===")
            print(f"Current user data: {self.user_data}")  # Debug user_data contents
            
            current_row = user_table.currentRow()
            print(f"Selected row index: {current_row}")
            
            if current_row < 0:
                print("ERROR: No row selected")
                QMessageBox.warning(dialog, "Error", "Please select a user to delete")
                return
            
            try:
                # Get user information
                print("Retrieving user information from table...")
                email_item = user_table.item(current_row, 0)
                role_item = user_table.item(current_row, 1)
                
                print(f"Email item type: {type(email_item)}")
                print(f"Role item type: {type(role_item)}")
                
                if not email_item or not role_item:
                    print("ERROR: Could not get email or role item from table")
                    QMessageBox.warning(dialog, "Error", "Could not retrieve user information")
                    return
                
                user_email = email_item.text().strip()
                print(f"User email (raw): {email_item.text()}")
                print(f"User email (stripped): {user_email}")
                
                if not user_email:
                    print("ERROR: Empty user email after stripping")
                    QMessageBox.warning(dialog, "Error", "Invalid user email")
                    return
                    
                # Fix role extraction - get raw text and convert to lowercase
                raw_role = role_item.text()
                print(f"User role (raw): {raw_role}")
                
                user_role = raw_role.lower()
                if "account type:" in user_role:
                    user_role = user_role.replace("account type:", "").strip()
                print(f"User role (processed): {user_role}")
                
                # Check if trying to delete own account - safely get email
                current_user_email = self.user_data.get('email', '')
                print(f"Current user email: {current_user_email}")
                
                if user_email == current_user_email:
                    print("ERROR: Attempting to delete own account")
                    QMessageBox.warning(
                        dialog,
                        "Error",
                        "You cannot delete your own account"
                    )
                    return
                
                # Check role-based permissions - safely get role
                current_user_role = self.user_data.get('role', '')
                print(f"Current user role: {current_user_role}")
                
                if not current_user_role:
                    print("ERROR: No role found in user_data")
                    QMessageBox.warning(
                        dialog,
                        "Error",
                        "Session error: No role found. Please log out and log in again."
                    )
                    return
                
                if current_user_role == 'admin':
                    if user_role in ['root', 'admin']:
                        print("ERROR: Admin attempting to delete root/admin account")
                        QMessageBox.warning(
                            dialog,
                            "Permission Denied",
                            "As an admin, you can only delete moderator and user accounts"
                        )
                        return
                elif current_user_role == 'root':
                    if user_role == 'root':
                        print("ERROR: Attempting to delete root account")
                        QMessageBox.warning(
                            dialog,
                            "Permission Denied",
                            "Root accounts cannot be deleted"
                        )
                        return
                
                # Show confirmation dialog with user details
                print("Showing confirmation dialog...")
                confirm_msg = (
                    f"Are you sure you want to delete the following user?\n\n"
                    f"Email: {user_email}\n"
                    f"Role: {user_role.upper()}\n\n"
                    "This action cannot be undone!"
                )
                
                reply = QMessageBox.question(
                    dialog,
                    "Confirm User Deletion",
                    confirm_msg,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                print(f"User reply to confirmation: {reply == QMessageBox.Yes}")
                
                if reply == QMessageBox.Yes:
                    # Attempt to delete the user
                    print(f"Attempting to delete user {user_email}...")
                    success = self.user_manager.delete_user(self.user_token, user_email)
                    print(f"Delete operation result: {success}")
                    
                    if success:
                        # Remove the row from the table
                        print("Removing row from table...")
                        user_table.removeRow(current_row)
                        
                        QMessageBox.information(
                            dialog,
                            "Success",
                            f"User {user_email} has been deleted successfully"
                        )
                        
                        # Refresh the user table to ensure consistency
                        print("Refreshing user management view...")
                        dialog.accept()
                        self.show_user_management()
                    else:
                        print("ERROR: Delete operation failed")
                        error_msg = (
                            f"Failed to delete user {user_email}.\n\n"
                            f"This could be due to:\n"
                            f"• Invalid or expired session token\n"
                            f"• User has special permissions that prevent deletion\n"
                            f"• Database access error\n\n"
                            f"Please try logging out and back in, then try again."
                        )
                        QMessageBox.critical(
                            dialog,
                            "Error",
                            error_msg
                        )
                        
            except Exception as e:
                print("\n=== Unexpected error in handle_delete_user ===")
                print(f"Error type: {type(e)}")
                print(f"Error message: {str(e)}")
                print("Stack trace:")
                import traceback
                traceback.print_exc()
                print("===========================================")
                
                error_msg = (
                    f"An unexpected error occurred while trying to delete user {user_email}:\n\n"
                    f"{str(e)}\n\n"
                    f"Please try:\n"
                    f"• Refreshing the user management page\n"
                    f"• Logging out and back in\n"
                    f"• Contacting system administrator if the problem persists"
                )
                QMessageBox.critical(
                    dialog,
                    "Error",
                    error_msg
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
        
        def show_export_dialog():
            """Show export type selection dialog"""
            export_dialog = QDialog(dialog)
            export_dialog.setWindowTitle("Export Data")
            export_dialog.setModal(True)
            
            export_layout = QVBoxLayout(export_dialog)
            
            # Add descriptive label
            label = QLabel("Select export format:")
            label.setStyleSheet("font-size: 12px; margin-bottom: 10px;")
            export_layout.addWidget(label)
            
            # Create export type buttons
            excel_btn = QPushButton("Excel Format (.xlsx)")
            csv_btn = QPushButton("CSV Format (.csv)")
            json_btn = QPushButton("JSON Format (.json)")
            
            # Style the buttons
            button_style = """
                QPushButton {
                    padding: 10px;
                    margin: 5px;
                    text-align: left;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #f8f9fa;
                }
            """
            excel_btn.setStyleSheet(button_style)
            csv_btn.setStyleSheet(button_style)
            json_btn.setStyleSheet(button_style)
            
            export_layout.addWidget(excel_btn)
            export_layout.addWidget(csv_btn)
            export_layout.addWidget(json_btn)
            
            # Connect buttons to export function
            excel_btn.clicked.connect(lambda: export_data('excel', export_dialog))
            csv_btn.clicked.connect(lambda: export_data('csv', export_dialog))
            json_btn.clicked.connect(lambda: export_data('json', export_dialog))
            
            export_dialog.exec()
        
        def export_data(export_type, export_dialog):
            """Export user table data to specified format"""
            try:
                # Get all data from the table
                data = []
                for row in range(user_table.rowCount()):
                    row_data = {
                        'Email': user_table.item(row, 0).text(),
                        'Account Type': user_table.item(row, 1).text(),
                        'Created': user_table.item(row, 3).text(),
                        'Last Login': user_table.item(row, 4).text()
                    }
                    data.append(row_data)
                
                # Create DataFrame
                df = pd.DataFrame(data)
                
                # Get file path from user
                file_filters = {
                    'excel': "Excel Files (*.xlsx)",
                    'csv': "CSV Files (*.csv)",
                    'json': "JSON Files (*.json)"
                }
                
                file_path, _ = QFileDialog.getSaveFileName(
                    dialog,
                    f"Export as {export_type.upper()}",
                    "",
                    file_filters[export_type]
                )
                
                if file_path:
                    if export_type == 'excel':
                        df.to_excel(file_path, index=False)
                    elif export_type == 'csv':
                        df.to_csv(file_path, index=False)
                    elif export_type == 'json':
                        df.to_json(file_path, orient='records', indent=2)
                    
                    QMessageBox.information(
                        dialog,
                        "Success",
                        f"Data exported successfully to {file_path}"
                    )
                    export_dialog.accept()  # Close the export dialog after successful export
            except Exception as e:
                QMessageBox.warning(
                    dialog,
                    "Export Error",
                    f"Failed to export data: {str(e)}"
                )
        
        # Connect buttons
        add_user.clicked.connect(handle_add_user)
        delete_user.clicked.connect(handle_delete_user)
        reset_password.clicked.connect(handle_reset_password)
        export_button.clicked.connect(show_export_dialog)
        
        dialog.exec()
    
    def load_data(self):
        """Load data into table"""
        try:
            # Get active schema
            active_schema = self.data_manager.schema_manager.get_active_schema(self.user_token)
            if not active_schema:
                self.table.setColumnCount(0)
                self.table.setRowCount(0)
                self.status_bar.showMessage("No active schema defined")
                return
            
            # Get data
            data = self.data_manager.get_data(self.user_token, self.current_page, self.page_size)
            
            # Set up table
            columns = active_schema["columns"]
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels([col["name"] for col in columns])
            
            # Set data
            records = data["data"]
            self.table.setRowCount(len(records))
            
            for row, record in enumerate(records):
                for col, column_def in enumerate(columns):
                    value = record.get(column_def["name"])
                    # Handle null values
                    if value is None:
                        item = QTableWidgetItem("")
                    else:
                        item = QTableWidgetItem(str(value))
                    self.table.setItem(row, col, item)
            
            # Update status bar
            total_records = data["metadata"]["row_count"]
            total_pages = data["pagination"]["total_pages"]
            self.status_bar.showMessage(
                f"Total Records: {total_records} | "
                f"Page {self.current_page} of {total_pages} | "
                f"Active Schema: {active_schema['metadata']['name']}"
            )
            
            # Update navigation buttons
            self.prev_button.setEnabled(self.current_page > 1)
            self.next_button.setEnabled(self.current_page < total_pages)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
            self.status_bar.showMessage("Error loading data")
    
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