# Secure Database Management System

A robust and secure database management system built with Python and PySide6, featuring role-based access control, encrypted data storage, and comprehensive security features.

## 🌟 Key Features

### Security
- **Advanced Encryption**
  - AES-GCM encryption for all data files
  - PBKDF2-HMAC-SHA256 key derivation
  - Unique installation salt
  - Bcrypt password hashing

- **Role-Based Access Control**
  - Hierarchical role system (Root, Admin, Moderator, User)
  - Granular permission management
  - Operation-based access control
  - Role inheritance

- **Session Management**
  - 24-hour encrypted session tokens
  - Automatic session expiration
  - Secure token validation
  - Account lockout protection

### User Management
- **Account Security**
  - Account lockout after 5 failed attempts
  - 15-minute lockout duration
  - Password complexity requirements
  - Secure password reset mechanism

- **User Administration**
  - Role-based user management
  - User activity tracking
  - Last login monitoring
  - Creation attribution

### Data Management
- **Secure Storage**
  - Encrypted schema storage
  - Encrypted database files
  - Secure configuration management
  - Automatic backup support

- **Data Operations**
  - Excel file import/export
  - Schema validation
  - Data type verification
  - Bulk operations support

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- Git
- Virtual environment (recommended)

### Installation

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd [project-directory]
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Unix or MacOS:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Initial Setup

1. Run the initialization script:
   ```bash
   python src/initialize_project.py
   ```

2. Follow the prompts to configure:
   - Company information
   - Admin credentials
   - Security settings
   - Database location

## 🔒 Security Features

### Encryption System
- **File Encryption**
  - AES-GCM for file encryption
  - Unique nonce for each encryption
  - Authenticated encryption
  - Secure key derivation

- **Password Security**
  - Bcrypt password hashing
  - Salt-based key derivation
  - Configurable password policies
  - Secure password reset

### Access Control
- **Role Hierarchy**
  ```
  Root
   └── Admin
        └── Moderator
             └── User
  ```

- **Permission Matrix**
  | Operation        | Root | Admin | Moderator | User |
  |------------------|------|-------|-----------|------|
  | Read Data        | ✓    | ✓     | ✓         | ✓    |
  | Write Data       | ✓    | ✓     | ✓         | ✘    |
  | Delete Data      | ✓    | ✓     | ✘         | ✘    |
  | Modify Schema    | ✓    | ✓     | ✘         | ✘    |
  | Manage Users     | ✓    | ✓*    | ✘         | ✘    |
  | Reset Passwords  | ✓    | ✓*    | ✘         | ✘    |
  
  *Admin can only manage lower-level roles

### Session Management
- 24-hour session duration
- Encrypted session tokens
- Automatic expiration
- Secure token validation

## 📁 Project Structure

```
project_root/
├── data/               # Encrypted data storage
│   ├── security/      # Security-related files
│   └── users/         # User data storage
├── docs/              # Documentation
├── logs/              # Application logs
├── resources/         # Application resources
│   └── company/       # Company-specific assets
├── src/               # Source code
│   ├── core/          # Core functionality
│   │   ├── data_manager.py
│   │   ├── security_manager.py
│   │   └── user_manager.py
│   ├── ui/           # User interface
│   │   ├── login_window.py
│   │   ├── main_window.py
│   │   └── styles.qss
│   └── main.py       # Application entry
└── requirements.txt   # Python dependencies
```

## 🛠 Configuration

### Environment Variables
Required environment variables:
- `MASTER_PASSWORD`: Master encryption key
- `ROOT_EMAIL`: Initial root user email
- `ROOT_PASSWORD`: Initial root password
- `USERS_FILE`: Path to users database

Optional configurations:
- `SESSION_DURATION_HOURS`: Default 24
- `MIN_PASSWORD_LENGTH`: Default 8
- `LOCKOUT_DURATION`: Default 15 minutes

### Security Settings
Password requirements:
- Minimum 8 characters
- Uppercase and lowercase letters
- Numbers and special characters
- No common patterns

## 📝 Logging

The system maintains detailed logs for:
- Security events
- User operations
- Database transactions
- System errors

Log files are stored in the `logs/` directory with UTC timestamps.

## 🔄 Backup and Recovery

### Backup Requirements
Critical files to backup:
- Encrypted database files
- Salt file
- Configuration files
- Environment variables

### Recovery Process
1. Restore encrypted files
2. Verify salt file
3. Configure environment variables
4. Test system access

## 🚨 Troubleshooting

### Common Issues

1. **Encryption Errors**
   ```
   Error: Decryption failed. Invalid password or corrupted data.
   ```
   - Verify master password
   - Check salt file integrity
   - Ensure file permissions

2. **Permission Issues**
   ```
   Error: Permission denied
   ```
   - Check file ownership
   - Verify directory permissions
   - Ensure proper access rights

3. **Authentication Failures**
   ```
   Error: Account is locked
   ```
   - Wait for lockout period
   - Verify credentials
   - Check account status

## 📄 License

This project is licensed under the terms specified in the LICENSE file.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📚 Documentation

Additional documentation available in the `docs/` directory:
- Logging System Details
- Role-Based User Management System
