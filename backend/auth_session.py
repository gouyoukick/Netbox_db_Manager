# === backend/auth_session.py ===

_ssh_user = None
_sudo_password = None

def set_ssh_credentials(user, password):
    global _ssh_user, _sudo_password
    _ssh_user = user
    _sudo_password = password

def get_ssh_credentials():
    return _ssh_user, _sudo_password

def is_ssh_credentials_set():
    return _ssh_user is not None and _sudo_password is not None
