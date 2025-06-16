# === import_utils.py === (version finale sans debug)

import subprocess
from pathlib import Path

GIT_SSH = "C:/Program Files/Git/usr/bin/ssh.exe"
SSH_KEY = str(Path.home() / ".ssh" / "id_rsa")


def import_database_with_verification(source, ssh_user, sudo_password, chemin_fichier_sql):
    return {
        "status": "todo",
        "step": "non implémenté",
        "message": "Import non encore implémenté"
    }


def verifier_docker_actif(ip, ssh_user, sudo_password, container_name):
    cmd = f"echo {sudo_password} | sudo -S /usr/local/bin/docker ps --format '{{{{.Names}}}}'"
    try:
        result = subprocess.run([GIT_SSH, "-i", SSH_KEY, f"{ssh_user}@{ip}", cmd],
                                capture_output=True, text=True, timeout=10)
        all_containers = result.stdout.strip().splitlines()
        return any(container_name in name for name in all_containers)
    except Exception:
        return False


def creer_dossier_distant(ip, ssh_user, sudo_password, chemin_dossier):
    cmd = f"echo {sudo_password} | sudo -S mkdir -p '{chemin_dossier}'"
    try:
        result = subprocess.run([GIT_SSH, "-i", SSH_KEY, f"{ssh_user}@{ip}", cmd],
                                capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False


def copier_fichier_vers_distant(chemin_local, ssh_user, ip, chemin_distant):
    try:
        with open(chemin_local, "rb") as f:
            result = subprocess.run([
                GIT_SSH, "-i", SSH_KEY,
                f"{ssh_user}@{ip}", f"cat > {chemin_distant}"
            ], input=f.read(), capture_output=True, timeout=20)

        return result.returncode == 0
    except Exception:
        return False
