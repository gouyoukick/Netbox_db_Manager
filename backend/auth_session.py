# backend/auth_session.py

import getpass

_ssh_user = None
_sudo_password = None

def get_ssh_credentials():
    global _ssh_user, _sudo_password

    if _ssh_user is None:
        _ssh_user = input("Entrez le nom d’utilisateur SSH : ").strip()

    if _sudo_password is None:
        _sudo_password = getpass.getpass("Entrez le mot de passe sudo : ")

    return _ssh_user, _sudo_password
