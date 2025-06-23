# Template Database Management System

A customizable and secure database management system template built with Python and PySide6. This template provides a foundation for building company-specific database applications with role-based access control, encrypted data storage, and Excel data import capabilities.

## Template Overview

This project serves as a starting point for creating customized database applications. It can be adapted for different companies and use cases while maintaining core security features and functionality.

### Customization Points

- **Branding**
  - Company logos and icons
  - Application name and titles
  - UI text and labels
  - Copyright information

- **Business Logic**
  - Database schema
  - Data validation rules
  - Import/Export formats
  - Custom business rules

- **Security**
  - Role definitions
  - Access control rules
  - Password policies
  - Encryption settings

## Project Initialization

### Prerequisites

Before initializing the project for a new customer, ensure you have:
- Python 3.8 or higher installed
- Git installed
- Basic understanding of database schemas
- Company assets (logo and icon) ready

### Initial Setup

1. Clone the template:
   ```bash
   git clone [repository-url]
   cd [project-directory]
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Initialization Script

1. Start the initialization process:
   ```bash
   python src/initialize_project.py
   ```

2. The script will guide you through:
   - Company information setup
   - Admin account creation
   - Security configuration
   - Resource placement

3. You will be prompted for:
   - Company name
   - Admin email
   - Support email
   - Copyright year
   - Master password (for database encryption)
   - Admin password

### Detailed Initialization Settings

The initialization process creates several important configuration settings that you should carefully consider:

#### Security Settings

1. **Master Password**
   - This is the encryption key for all database files
   - Must be strong and securely stored
   - Used for encrypting: schema, user data, and configuration files
   - Cannot be recovered if lost - all data will be inaccessible
   - Must meet password complexity requirements
   - Recommendation: Use a password manager to generate and store this

2. **Session Configuration**
   - `SESSION_DURATION_HOURS`: Default is 24 hours
   - Controls how long users can stay logged in
   - Can be modified in `.env` file after initialization
   - Shorter duration increases security, longer improves user experience
   - Account lockout after 5 failed login attempts
   - 15-minute lockout duration for security

3. **Password Requirements**
   - `MIN_PASSWORD_LENGTH`: Default is 8 characters
   - Must contain uppercase and lowercase letters
   - Must contain numbers and special characters
   - Applied to both admin and user passwords
   - Can be strengthened by modifying `.env` file
   - Recommendation: Use at least 12 characters for production

4. **Security Logging**
   - All security events are logged with UTC timestamps
   - Failed login attempts are tracked
   - Account lockouts are recorded
   - Encryption/decryption operations are monitored
   - Logs are stored in the logs/ directory

#### File Structure

1. **Encrypted Files**
   - All sensitive files are stored in the `data/` directory:
     - `users.enc`: User account information
     - `database.enc`: Main database content
     - `schema.enc`: Database schema definition
     - `config.enc`: System configuration
   - Files use AES-GCM encryption
   - Each file requires master password for access

2. **Salt File**
   - Located at `data/salt.key`
   - Automatically generated during initialization
   - Critical for password hashing
   - Should be backed up securely

#### Account Settings

1. **Admin Account**
   - `ADMIN_EMAIL`: Primary administrator email
   - Used for system notifications and recovery
   - Should be a monitored, secure email address
   - Can be changed later through the application

2. **Support Email**
   - Used for user support communications
   - Displayed in the application interface
   - Can be department email or help desk
   - Modifiable in `.env` file

#### Company Information

1. **Company Assets**
   - Logo requirements:
     - Format: PNG
     - Location: `resources/company/logo.png`
     - Recommended size: 200x200 pixels
   - Icon requirements:
     - Format: ICO
     - Location: `resources/company/icon.ico`
     - Recommended size: 32x32 pixels

2. **Company Identity**
   - `COMPANY_NAME`: Displayed throughout the application
   - `COPYRIGHT_YEAR`: Used in legal notices
   - Both can be updated in `.env` file

#### Customizing Settings Post-Initialization

You can modify most settings after initialization by editing the `.env` file:

1. Security Adjustments:
   ```plaintext
   SESSION_DURATION_HOURS=12  # Reduce session duration
   MIN_PASSWORD_LENGTH=12     # Increase minimum password length
   ```

2. Company Information Updates:
   ```plaintext
   COMPANY_NAME="Updated Company Name"
   SUPPORT_EMAIL="new.support@company.com"
   ```

3. File Location Changes:
   ```plaintext
   USERS_FILE=custom/path/users.enc
   DATABASE_FILE=custom/path/database.enc
   ```

#### Important Notes

1. **Backup Considerations**
   - Keep secure backups of:
     - Master password
     - Salt file
     - Encrypted data files
     - Environment configuration

2. **Security Best Practices**
   - Change the admin password regularly
   - Use strong passwords for all accounts
   - Keep the `.env` file secure and backed up
   - Regularly audit user accounts and permissions

3. **Recovery Preparation**
   - Document the master password securely
   - Maintain backup procedures for encrypted files
   - Keep recovery email addresses updated
   - Test the recovery process periodically

#### Troubleshooting Common Initialization Issues

1. **Master Password Issues**
   ```
   Error: Decryption failed. Invalid password or corrupted data.
   ```
   - **Cause**: Incorrect master password or corrupted encryption files
   - **Solutions**:
     - Verify no special characters are being truncated in the password
     - Check if the password was copied correctly (no extra spaces)
     - Ensure the salt.key file hasn't been modified
     - If setting up fresh: delete all .enc files and restart initialization

2. **Directory Permission Errors**
   ```
   Error: Permission denied: 'data/users.enc'
   ```
   - **Cause**: Insufficient write permissions
   - **Solutions**:
     - Check folder permissions (especially data/ and resources/)
     - Run as administrator if necessary
     - Verify user has write access to project directory
     - On Linux/Mac: `chmod -R 755 data/ resources/`

3. **Resource File Issues**
   ```
   Error: Cannot load company logo/icon
   ```
   - **Cause**: Missing or invalid resource files
   - **Solutions**:
     - Verify logo.png and icon.ico exist in resources/company/
     - Check file formats (PNG for logo, ICO for icon)
     - Ensure files aren't corrupted
     - Try using the dummy resources as templates

4. **Environment File Problems**
   ```
   Error: No .env file found
   ```
   - **Cause**: Missing or inaccessible .env file
   - **Solutions**:
     - Run initialization script again
     - Create .env manually from .env.example
     - Check file permissions
     - Verify no hidden characters in file name

5. **Database Initialization Failures**
   ```
   Error: Could not initialize database structure
   ```
   - **Cause**: Issues with data directory or encryption
   - **Solutions**:
     - Verify data/ directory exists and is writable
     - Check if all required .enc files are created
     - Ensure master password is consistent
     - Delete and recreate data/ directory if necessary

6. **Python Environment Issues**
   ```
   Error: ModuleNotFoundError: No module named 'cryptography'
   ```
   - **Cause**: Missing dependencies or virtual environment problems
   - **Solutions**:
     - Activate virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
     - Reinstall requirements: `pip install -r requirements.txt`
     - Check Python version compatibility (3.8+ required)
     - Create new virtual environment if corrupted

7. **Admin Account Setup Issues**
   ```
   Error: Could not create admin account
   ```
   - **Cause**: Invalid input or encryption problems
   - **Solutions**:
     - Use valid email format for admin email
     - Ensure password meets minimum requirements
     - Check if users.enc file is writable
     - Verify master password is working

8. **Salt Generation Problems**
   ```
   Error: Could not generate salt file
   ```
   - **Cause**: System entropy or permission issues
   - **Solutions**:
     - Check write permissions for data directory
     - Ensure enough system entropy (especially on Linux)
     - Try running with elevated privileges
     - Manually create salt.key with: `python -c "import os; open('data/salt.key', 'wb').write(os.urandom(32))"`

9. **Configuration File Corruption**
   ```
   Error: Invalid configuration format
   ```
   - **Cause**: Corrupted or invalid .env file
   - **Solutions**:
     - Delete .env and run initialization again
     - Copy from .env.example and fill in values
     - Check for invalid characters in configuration
     - Verify file encoding is UTF-8

10. **Memory/Resource Issues**
    ```
    Error: MemoryError during initialization
    ```
    - **Cause**: Insufficient system resources
    - **Solutions**:
      - Close other applications
      - Check available system memory
      - Reduce other system load
      - Try on a machine with more resources

#### Recovery Steps

If initialization fails completely:

1. Clean Start:
   ```bash
   rm -rf data/*
   rm .env
   rm -rf resources/company/*
   ```

2. Verify Prerequisites:
   ```bash
   python --version  # Should be 3.8+
   pip list         # Check installed packages
   ```

3. Reinitialize:
   ```bash
   python src/initialize_project.py
   ```

4. Verify Structure:
   ```bash
   ls data/         # Should see .enc files
   ls resources/company/  # Should see logo and icon
   cat .env         # Should see all required settings
   ```

### Directory Structure Created

The initialization script creates the following structure:
```
project_root/
├── data/               # Encrypted database files
│   ├── users.enc
│   ├── database.enc
│   ├── schema.enc
│   └── db_config.enc
├── logs/              # Application logs
├── resources/
│   └── company/       # Company-specific assets
│       ├── logo.png
│       └── icon.ico
└── .env              # Environment configuration
```

### Post-Initialization Steps

1. Replace Company Assets:
   - Place company logo at `resources/company/logo.png`
   - Place company icon at `resources/company/icon.ico`
   - Ensure images match required dimensions and formats

2. Review Configuration:
   - Check `.env` file for correct settings
   - Adjust security parameters if needed
   - Verify file paths and permissions

3. First Run:
   ```bash
   python src/main.py
   ```

4. Initial Setup in Application:
   - Log in with admin credentials
   - Define database schema
   - Create additional user accounts
   - Configure access permissions
   - Set up initial data structure

### Security Notes for Initialization

- The `.env` file contains sensitive information - secure it appropriately
- All encryption keys and passwords should be stored securely
- The `data/` directory will contain encrypted database files
- Company assets should be backed up separately
- Initial admin credentials should be changed after first login

### Troubleshooting Initialization

If you encounter issues during initialization:
1. Check Python version compatibility
2. Verify all dependencies are installed
3. Ensure write permissions in project directories
4. Validate company asset formats
5. Check environment variable configuration

## Features

- **Secure Authentication**
  - Customizable role-based access control
  - Password hashing using bcrypt
  - Session-based authentication with encrypted tokens

- **Data Security**
  - AES-GCM encryption for data storage
  - PBKDF2 key derivation for file encryption
  - Secure password management

- **User Interface**
  - Modern Qt-based GUI using PySide6
  - Customizable design elements
  - Dark theme support
  - Brandable components

- **Data Management**
  - Configurable Excel file import with schema validation
  - Pagination for large datasets
  - CRUD operations for records (based on user role)
  - Custom schema definition

- **Administrative Features**
  - User management (Admin only)
  - Schema definition (Admin only)
  - Database configuration
  - Password reset capabilities

## Project Structure

```
DB_Project/
├── requirements.txt        # Python dependencies
├── resources/             # Customizable resources
│   ├── dummy-logo.ico     # Placeholder icon (replaceable)
│   └── dummy-logo.png     # Placeholder logo (replaceable)
└── src/                   # Source code
    ├── core/              # Core functionality
    │   ├── data_manager.py    # Data handling and encryption
    │   ├── security_manager.py # Security and authentication
    │   └── user_manager.py    # User management
    ├── ui/                # User interface
    │   ├── login_window.py    # Login interface
    │   ├── main_window.py     # Main application window
    │   └── styles.qss         # Customizable styling
    └── main.py           # Application entry point
```

## Technical Details

### Security Features

- **File Encryption**
  - Uses AES-GCM for file encryption
  - PBKDF2-HMAC-SHA256 for key derivation
  - Unique salt for each installation
  - Encrypted storage for schema and data files

- **Authentication**
  - Bcrypt password hashing
  - 24-hour session tokens
  - Brute force protection with account lockout
  - Strong password policy enforcement
  - Configurable role-based access control
  - Secure password reset mechanism

- **Security Logging**
  - Comprehensive security event logging
  - Encryption/decryption operation tracking
  - Failed login attempt monitoring
  - Account lockout events
  - Timezone-aware timestamps (UTC)

### Session Management

- **Session Security**
  - 24-hour session duration
  - Encrypted session tokens
  - Automatic session expiration
  - Secure token validation
  - Account lockout after 5 failed attempts
  - 15-minute lockout duration

- **Account Protection**
  - Failed login attempt tracking
  - Automatic account unlocking
  - Clear lockout duration display
  - Secure session cleanup

### Password Requirements

- Minimum 8 characters length
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- Password strength validation on creation and change

### Data Management

- **Schema Management**
  - Custom schema definition
  - Support for string, number, and date data types
  - Excel column mapping
  - Schema validation during import

- **Data Operations**
  - Paginated data access
  - Record-level CRUD operations
  - Bulk import from Excel files
  - Data type validation and conversion

## Customization Guide

1. **Branding Customization**
   - Replace placeholder logos in `/resources`
   - Update application title in `main_window.py`
   - Modify copyright information in `login_window.py`
   - Customize UI text and labels throughout the application

2. **Business Logic Customization**
   - Define company-specific database schema
   - Implement custom data validation rules
   - Add specific business logic in core modules
   - Customize data import/export formats

3. **Security Customization**
   - Configure role-based permissions
   - Set up password policies
   - Define access control rules
   - Customize encryption settings

## Installation

1. Clone the template:
   ```bash
   git clone [repository-url]
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Development Setup

1. Start the application:
   ```bash
   python src/main.py
   ```

2. Default admin credentials:
   - Email: admin@company.com
   - Password: (Set during initial setup)

3. Customize the application:
   - Replace branding assets
   - Configure database schema
   - Set up user roles
   - Implement custom features

## User Roles and Management

### Role Hierarchy

1. **Root**
   - Full system access
   - Can create/modify/delete any users (except other root users)
   - Can create admin, moderator, and user roles
   - Schema definition
   - Database configuration
   - Data management
   - Cannot be deleted or modified by other users

2. **Admin**
   - User management (limited)
     - Can create/modify/delete moderator and user roles only
     - Cannot modify root or other admin users
   - Schema definition
   - Database configuration
   - Data management
   - Full data access

3. **Moderator**
   - Data import capabilities
   - Record management
   - Data viewing
   - Limited user management access

4. **User**
   - Data viewing
   - Password management
   - Limited system access

### User Management Features

1. **User Interface**
   - Modern, filterable user management table
   - Role-specific color coding:
     * Root: Blue (#0078d4)
     * Admin: Green (#28a745)
     * Moderator: Yellow (#ffc107)
     * User: Purple (#6f42c1)
   - Visual indicators for non-modifiable users (red text)
   - Fullscreen capability

2. **Search and Filtering**
   - Email search filter
   - Role-based filtering
   - Date range filter for user creation date
   - Column sorting
   - Clear filters option

3. **User Operations**
   - Add new users with role assignment
   - Delete users (with role-based restrictions)
   - Reset user passwords
   - Change user roles
   - View user creation date and last login

4. **Security Features**
   - Account lockout after 5 failed login attempts
   - 15-minute lockout duration
   - Secure password reset mechanism
   - Role-based access control
   - Session-based authentication
   - Password complexity requirements

5. **Audit Trail**
   - User creation tracking
   - Last login timestamps
   - Role modification history
   - Creation and modification attribution

### Password Management

1. **Password Requirements**
   - Minimum 8 characters length
   - At least one uppercase letter
   - At least one lowercase letter
   - At least one number
   - At least one special character
   - Password strength validation

2. **Password Operations**
   - Self-service password change
   - Admin/Root password reset capability
   - Secure password hashing using bcrypt
   - Password confirmation for changes

### Session Management

- 24-hour session duration
- Encrypted session tokens
- Automatic session expiration
- Secure token validation
- Account lockout protection
- Clear lockout duration display

## Dependencies

- PySide6: Qt-based GUI framework
- bcrypt: Password hashing
- cryptography: Data encryption
- pandas: Excel file processing
- python-dotenv: Environment variable management

## Security Notes

- All data files are encrypted at rest
- Passwords are never stored in plain text
- Session tokens expire after 24 hours
- File operations are protected by role-based access control
- Sensitive operations require re-authentication

## Template Version

- Database Schema Version: 1.0
- Template Version: 1.0

## License

This template is provided as a starting point for custom database applications. Ensure proper licensing and attribution when creating derivative works. 