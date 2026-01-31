from __init__ import USBTransferService, USBDevice, DataExport

# Singleton service instance
_service = USBTransferService()

# Expose module level convenience functions and attributes used by main.py
def authenticate(password: str):
    return _service.authenticate(password)

def validate_session(token: str):
    return _service.validate_session(token)

def change_password(session_token: str, old_password: str, new_password: str):
    return _service.change_password(session_token, old_password, new_password)

def scan_usb_devices():
    return _service.scan_usb_devices()

def export_therapy_progress(session_token: str, device_id: str, data):
    return _service.export_therapy_progress(session_token, device_id, data)

def import_data(session_token: str, device_id: str, import_type: str):
    return _service.import_data(session_token, device_id, import_type)

def get_export_history(session_token: str):
    return _service.get_export_history(session_token)

def cleanup_expired_sessions():
    return _service.cleanup_expired_sessions()

# Attributes
active_sessions = _service.active_sessions
mounted_devices = _service.mounted_devices
config_path = _service.config_path
