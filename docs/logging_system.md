# Logging System Documentation

## 📑 Table of Contents
1. [Overview](#overview)
2. [Log Types](#log-types)
3. [Log Structure](#log-structure)
4. [Configuration](#configuration)
5. [Log Rotation](#log-rotation)
6. [Usage Guide](#usage-guide)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The logging system is a centralized mechanism for recording various events and operations within the application. It provides consistent logging across all components while ensuring proper organization and rotation of log files.

### Key Features
- 🔄 Automatic log rotation
- 📁 Organized log categories
- 🔒 Security event tracking
- 📊 Operation monitoring
- ⚡ High-performance logging

## Log Types

### 1. Security Logs (`security.log`)
- Authentication attempts
- Session management
- Permission checks
- Encryption operations
- Security violations

Example:
```
2024-03-15 14:30:22 - security_manager - WARNING - LOGIN_FAILED: Maximum attempts exceeded for user@example.com
2024-03-15 14:35:45 - security_manager - INFO - TOKEN_VERIFIED: Session token validated for admin@example.com
```

### 2. Database Logs (`database.log`)
- Data operations
- Schema changes
- Query execution
- Backup operations
- Configuration updates

Example:
```
2024-03-15 15:20:10 - database_manager - INFO - SCHEMA_UPDATE: Added new column 'status' to users table
2024-03-15 15:22:30 - database_manager - ERROR - QUERY_FAILED: Invalid SQL syntax in update operation
```

### 3. User Operation Logs (`user.log`)
- User creation/deletion
- Role changes
- Profile updates
- Login/logout events
- Password changes

Example:
```
2024-03-15 16:10:05 - user_manager - INFO - USER_CREATED: New user john.doe@example.com created by admin
2024-03-15 16:15:22 - user_manager - INFO - ROLE_CHANGED: User role updated from user to moderator
```

### 4. System Logs (`system.log`)
- Application startup/shutdown
- Configuration changes
- System errors
- Performance metrics
- General operations

Example:
```
2024-03-15 09:00:00 - system - INFO - APPLICATION_START: System initialized successfully
2024-03-15 09:00:05 - system - INFO - CONFIG_LOADED: Environment variables loaded
```

## Log Structure

### Standard Log Format
```
{timestamp} - {component} - {level} - {event_type}: {details}
```

### Components
- **Timestamp**: UTC time in YYYY-MM-DD HH:MM:SS format
- **Component**: System component generating the log
- **Level**: Log severity (INFO, WARNING, ERROR, etc.)
- **Event Type**: Specific event identifier
- **Details**: Detailed event information

### Log Levels
1. **INFO**: Normal operations
   - Successful operations
   - State changes
   - Regular events

2. **WARNING**: Potential issues
   - Failed login attempts
   - Resource limitations
   - Deprecated features

3. **ERROR**: Operation failures
   - System errors
   - Security violations
   - Data corruption

4. **DEBUG**: Development information
   - Detailed operation flow
   - Variable states
   - Performance metrics

## Configuration

### Log Directory Structure
```
logs/
├── security.log       # Security events
├── database.log      # Database operations
├── user.log         # User operations
└── system.log       # General system events
```

### Rotation Settings
- Maximum file size: 10MB
- Backup count: 5 files
- Naming pattern: `{log_name}.log.{number}`

Example:
```
security.log
security.log.1
security.log.2
security.log.3
security.log.4
security.log.5
```

## Log Rotation

### Rotation Policy
- Size-based rotation (10MB per file)
- Keeps 5 backup files
- Automatic compression of old logs
- UTC timestamp preservation

### Rotation Process
1. Current log reaches 10MB
2. File is renamed to `.log.1`
3. Previous `.log.1` becomes `.log.2`
4. Process continues up to `.log.5`
5. Oldest log is deleted

## Usage Guide

### Basic Logging
```python
from core.logging_config import LogConfig

# Security event
LogConfig.log_security_event("LOGIN_ATTEMPT", "User login successful", "INFO")

# Database event
LogConfig.log_database_event("QUERY_EXECUTED", "Select operation completed", "INFO")

# User event
LogConfig.log_user_event("USER_CREATED", "New user account created", "INFO")
```

### Custom Logger Usage
```python
logger = LogConfig.get_logger("custom_component")
logger.info("Custom operation completed")
logger.warning("Resource usage high")
logger.error("Operation failed")
```

## Best Practices

### 1. Event Logging
- Use appropriate log levels
- Include relevant context
- Keep messages clear and concise
- Use consistent event types

### 2. Security Considerations
- Never log sensitive data
- Mask personal information
- Log security events immediately
- Maintain log file permissions

### 3. Performance
- Use appropriate log levels
- Avoid excessive logging
- Implement log rotation
- Monitor log file sizes

### 4. Maintenance
- Regular log review
- Periodic log cleanup
- Backup important logs
- Monitor disk space

## Troubleshooting

### Common Issues

#### 1. Log File Access
```
Error: Permission denied accessing log file
```
- **Solution**: Check file permissions
- **Prevention**: Set correct ownership

#### 2. Disk Space
```
Error: No space left on device
```
- **Solution**: Enable log rotation
- **Prevention**: Monitor disk usage

#### 3. Missing Logs
```
Error: Log file not found
```
- **Solution**: Verify log directory
- **Prevention**: Initialize logging properly

### Resolution Steps

1. **Permission Issues**
   - Check file ownership
   - Verify directory permissions
   - Set correct access rights

2. **Space Issues**
   - Enable log rotation
   - Increase rotation frequency
   - Monitor disk usage
   - Archive old logs

3. **Configuration Problems**
   - Verify log paths
   - Check configuration
   - Ensure proper initialization