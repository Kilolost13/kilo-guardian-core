# KILO USB Transfer Module

Secure USB data transfer module for the KILO AI Memory Assistant air-gapped system.

## Overview

This module provides secure data export and import capabilities for air-gapped KILO installations. It allows therapists and users to:

- Export therapy progress data to USB drives for sharing with healthcare providers
- Import bulk data from USB drives with integrity validation
- Maintain security through password protection and encryption
- Detect potentially infected USB drives

## Features

### Security Features
- **Password Protection**: All operations require authentication
- **Data Encryption**: Exported data is encrypted using Fernet (AES 128)
- **Integrity Validation**: SHA256 checksums for data integrity
- **USB Safety Checks**: Basic malware detection for USB drives
- **Session Management**: Automatic session timeout and cleanup

### Data Operations
- **Therapy Progress Export**: Export memories, habits, medications, and insights
- **Bulk Data Import**: Import data from external sources
- **Metadata Tracking**: Track export/import history and file information
- **Format Validation**: Ensure data conforms to expected schemas

## Installation

### Docker (Recommended)
```bash
cd usb_transfer
docker build -t kilo-usb-transfer .
docker run -p 8006:8006 -v /etc/kilo:/etc/kilo kilo-usb-transfer
```

### Local Installation
```bash
pip install -e .
kilo-usb
```

## Configuration

The service creates a default configuration on first run:
- **Location**: `/etc/kilo/usb_config.json`
- **Default Password**: Generated randomly (check logs on first run)
- **Security Settings**: Configurable timeouts, file size limits, allowed extensions

### Changing Password
```bash
curl -X POST http://localhost:8006/auth/change-password \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "current_password",
    "new_password": "new_secure_password"
  }'
```

## API Usage

### Authentication
```bash
# Get session token
curl -X POST http://localhost:8006/auth \
  -H "Content-Type: application/json" \
  -d '{"password": "your_password"}'
```

### Scan USB Devices
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8006/devices
```

### Export Therapy Data
```bash
curl -X POST http://localhost:8006/export \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "usb_device_id",
    "data": {
      "memories": [...],
      "habits": [...],
      "medications": [...]
    }
  }'
```

### Import Data
```bash
curl -X POST http://localhost:8006/import \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "usb_device_id",
    "import_type": "therapy_progress"
  }'
```

## USB Device Structure

### Export Structure
```
USB Drive/
└── kilo_exports/
    ├── therapy_progress_abc123_20231201_143022.kilo (encrypted)
    ├── therapy_progress_abc123_20231201_143022.sha256 (checksum)
    └── therapy_progress_abc123_20231201_143022.meta (metadata)
```

### Import Structure
```
USB Drive/
└── kilo_imports/
    ├── bulk_data_xyz789_20231201_150000.kilo (encrypted)
    ├── bulk_data_xyz789_20231201_150000.sha256 (checksum)
    └── bulk_data_xyz789_20231201_150000.meta (metadata)
```

## Security Considerations

### Password Policy
- Minimum 8 characters
- Should include uppercase, lowercase, numbers, and symbols
- Change default password immediately after setup

### USB Safety
- Service performs basic checks for suspicious files
- High ratio of hidden files triggers warnings
- Manual inspection recommended for unknown devices

### Data Encryption
- Uses Fernet encryption (AES 128 in CBC mode)
- Key derived from password using PBKDF2
- Checksums ensure data integrity

### Session Security
- Sessions expire after 30 minutes of inactivity
- Tokens are cryptographically secure random strings
- Automatic cleanup of expired sessions

## Integration with KILO

The USB transfer module integrates with the main KILO system through:

1. **Gateway Service**: Routes USB transfer requests
2. **Database Access**: Retrieves data for export
3. **Frontend Integration**: Admin interface for USB operations
4. **Docker Compose**: Included in main system orchestration

## Troubleshooting

### Common Issues

**USB Device Not Detected**
- Ensure device is properly mounted
- Check file permissions on mount point
- Verify device is formatted with supported filesystem

**Authentication Failed**
- Verify password is correct
- Check session hasn't expired (30 min timeout)
- Ensure config file exists and is readable

**Export/Import Failed**
- Check available disk space
- Verify file permissions
- Ensure data format is valid

### Logs
Check service logs for detailed error information:
```bash
docker logs kilo-usb-transfer
```

### Configuration Reset
To reset configuration (WARNING: This will change the password):
```bash
rm /etc/kilo/usb_config.json
# Restart service to generate new config
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black .
isort .
flake8 .
```

## License

This module is part of the KILO AI Memory Assistant system.