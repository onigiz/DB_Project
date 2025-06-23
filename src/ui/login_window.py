from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap

class LoginWindow(QMainWindow):
    # Signal emitted when login is successful
    login_successful = Signal(str, dict)
    
    def __init__(self, user_manager):
        super().__init__()
        self.user_manager = user_manager
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('General Secure Database')
        self.setFixedSize(500, 700)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(25)
        layout.setContentsMargins(40, 30, 40, 30)
        
        # Add Dummy logo
        logo_label = QLabel()
        logo_label.setObjectName('logoLabel')
        logo_pixmap = QPixmap('resources/dummy-logo.png')
        logo_label.setPixmap(logo_pixmap.scaledToWidth(180, Qt.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Add title label
        title_label = QLabel('Secure Database Login')
        title_label.setObjectName('titleLabel')
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Create form container with dark background
        form_container = QWidget()
        form_container.setObjectName('formContainer')
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(20)
        form_layout.setContentsMargins(30, 35, 30, 35)
        
        # Email input
        email_label = QLabel('Email:')
        email_label.setObjectName('inputLabel')
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('Enter your email')
        self.email_input.setMinimumHeight(45)
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        
        # Password input
        password_label = QLabel('Password:')
        password_label.setObjectName('inputLabel')
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Enter your password')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(45)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        
        # Error label
        self.error_label = QLabel('')
        self.error_label.setObjectName('errorLabel')
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        form_layout.addWidget(self.error_label)
        
        # Login button
        login_button = QPushButton('Login')
        login_button.clicked.connect(self.handle_login)
        login_button.setMinimumHeight(45)
        form_layout.addWidget(login_button)
        
        # Add form container to main layout
        layout.addWidget(form_container)
        
        # Add stretch to push footer to bottom
        layout.addStretch()
        
        # Add footer
        footer_layout = QVBoxLayout()
        footer_label = QLabel('© DummyCompany 2025')
        footer_label.setObjectName('footerLabel')
        footer_label.setAlignment(Qt.AlignCenter)
        footer_layout.addWidget(footer_label)
        
        reference_label = QLabel('@Onur Nigiz onurnigiz@hotmail.com 2025')
        reference_label.setObjectName('footerLabel')
        reference_label.setAlignment(Qt.AlignCenter)
        footer_layout.addWidget(reference_label)
        
        layout.addLayout(footer_layout)
        
        # Connect enter key to login
        self.email_input.returnPressed.connect(login_button.click)
        self.password_input.returnPressed.connect(login_button.click)
        
        # Set window icon
        self.setWindowIcon(QIcon('resources/dummy-logo.png'))
        
        # Center the window
        self.center_window()
        
    def center_window(self):
        """Center the window on the screen"""
        screen_geometry = self.screen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        
    def show_error(self, message):
        """Show error message"""
        self.error_label.setText(message)
        self.error_label.show()
        
    def clear_error(self):
        """Clear error message"""
        self.error_label.hide()
        self.error_label.clear()
        
    def handle_login(self):
        """Handle login button click"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        
        # Basic validation
        if not email or not password:
            self.show_error('Please enter both email and password')
            return
        
        # Attempt login
        result = self.user_manager.authenticate_user(email, password)
        if result:
            token, user_data = result
            self.login_successful.emit(token, user_data)
            self.close()
        else:
            self.show_error('Invalid email or password')
            self.password_input.clear()
            
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.close() 