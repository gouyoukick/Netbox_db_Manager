import subprocess
from pathlib import Path
import shutil
import os
from typing import Dict, Optional

from backend.hash_utils import compute_sha256
from backend.import_utils import _is_local_source

# Constants for SSH (NAS)
GIT_SSH = "C:/Program Files/Git/usr/bin/ssh.exe"
SSH_KEY = str(Path.home() / ".ssh" / "id_rsa")
SSH_OPTIONS = ["-o", "BatchMode=yes"]  # SSH key auth, no password prompts

# Directory for exports
EXPORT_DIR = Path("exported_database")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Fixed filenames for dumps
REMOTE_DUMP_PATH = "/tmp/exported_netbox_database.sql"
LOCAL_DUMP_NAME = "exported_netbox_database.sql"
TEMP_COPY_NAME = "temp_copy_exported_netbox_database.sql"


def verifier_sudo_password(
    ssh_user: Optional[str],
    sudo_password: Optional[str],
    remote_ip: str
) -> bool:
    """
    Vérifie le mot de passe sudo sur une machine distante :
    - Si l'instance est locale, on skip.
    - Sinon, on teste via SSH echo ... | sudo -S true.
    """
    ssh_user = ssh_user or ""
    sudo_password = sudo_password or ""

    # Skip for local sources
    if _is_local_source({"name": "local", "ip": remote_ip}):
        return True

    ssh_base = [GIT_SSH, *SSH_OPTIONS, "-i", SSH_KEY, f"{ssh_user}@{remote_ip}"]
    cmd = ssh_base + [f"echo '{sudo_password}' | sudo -S true"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0 and "sorry" not in res.stderr.lower()


def export_via_ssh_key(
    ip: str,
    ssh_user: Optional[str],
    sudo_password: Optional[str],
    container: str
) -> Dict:
    """
    Procédure NAS : SSH par clé + Docker exec/cp + sha256sum.
    """
    ssh_user = ssh_user or ""
    sudo_password = sudo_password or ""

    remote_dump = REMOTE_DUMP_PATH
    local_file = EXPORT_DIR / LOCAL_DUMP_NAME
    temp_copy = EXPORT_DIR / TEMP_COPY_NAME

    ssh_base = [GIT_SSH, *SSH_OPTIONS, "-i", SSH_KEY, f"{ssh_user}@{ip}"]

    # 1) Dump inside container
    dump_cmd = (
        f"echo '{sudo_password}' | sudo -S /usr/local/bin/docker exec {container} "
        f"pg_dump -U netbox-user netbox -f {remote_dump}"
    )
    res = subprocess.run(ssh_base + [dump_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "error", "step": "pg_dump", "message": res.stderr.strip()}

    # 2) docker cp to host
    cp_cmd = f"echo '{sudo_password}' | sudo -S /usr/local/bin/docker cp {container}:{remote_dump} {remote_dump}"
    res = subprocess.run(ssh_base + [cp_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "error", "step": "docker_cp", "message": res.stderr.strip()}

    # 3) remote SHA256
    hash_cmd = f"sha256sum {remote_dump}"
    res = subprocess.run(ssh_base + [hash_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "error", "step": "sha256_remote", "message": res.stderr.strip()}
    hash_remote = res.stdout.split()[0]

    # 4) fetch the dump via SSH
    with open(local_file, "wb") as f:
        res = subprocess.run(ssh_base + [f"cat {remote_dump}"], stdout=f, stderr=subprocess.PIPE)
    if res.returncode != 0:
        return {"status": "error", "step": "fetch", "message": res.stderr.decode().strip()}

    # 5) compute local SHA256 and compare
    shutil.copy(local_file, temp_copy)
    hash_local = compute_sha256(temp_copy)
    temp_copy.unlink(missing_ok=True)

    return {
        "status": "ok" if hash_local == hash_remote else "corrupted",
        "step": "complete",
        "remote_path": remote_dump,
        "local_path": str(local_file),
        "hash_remote": hash_remote,
        "hash_local": hash_local
    }


def export_via_ssh_passwd(
    ip: str,
    ssh_user: Optional[str],
    sudo_password: Optional[str],
    container: str
) -> Dict:
    """
    Procédure locale : SSH interactif (mot de passe) + Docker exec/cp + sha256sum.
    """
    ssh_user = ssh_user or ""
    sudo_password = sudo_password or ""

    remote_dump = REMOTE_DUMP_PATH
    local_file = EXPORT_DIR / LOCAL_DUMP_NAME
    temp_copy = EXPORT_DIR / TEMP_COPY_NAME

    # SSH command without key options for password auth
    ssh_base = ["ssh", f"{ssh_user}@{ip}"]

    # 1) pg_dump
    dump_cmd = (
        f"echo '{sudo_password}' | sudo -S docker exec {container} "
        f"pg_dump -U netbox-user netbox -f {remote_dump}"
    )
    res = subprocess.run(ssh_base + [dump_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "error", "step": "pg_dump", "message": res.stderr.strip()}

    # 2) docker cp
    cp_cmd = f"echo '{sudo_password}' | sudo -S docker cp {container}:{remote_dump} {remote_dump}"
    res = subprocess.run(ssh_base + [cp_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "error", "step": "docker_cp", "message": res.stderr.strip()}

    # 3) remote SHA256
    hash_cmd = f"sha256sum {remote_dump}"
    res = subprocess.run(ssh_base + [hash_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        return {"status": "error", "step": "sha256_remote", "message": res.stderr.strip()}
    hash_remote = res.stdout.split()[0]

    # 4) fetch the dump via SSH
    with open(local_file, "wb") as f:
        res = subprocess.run(ssh_base + [f"cat {remote_dump}"], stdout=f, stderr=subprocess.PIPE)
    if res.returncode != 0:
        return {"status": "error", "step": "fetch", "message": res.stderr.decode().strip()}

    # 5) compute local SHA256 and compare
    shutil.copy(local_file, temp_copy)
    hash_local = compute_sha256(temp_copy)
    temp_copy.unlink(missing_ok=True)

    return {
        "status": "ok" if hash_local == hash_remote else "corrupted",
        "step": "complete",
        "remote_path": remote_dump,
        "local_path": str(local_file),
        "hash_remote": hash_remote,
        "hash_local": hash_local
    }


def export_database_with_verification(
    source: Dict,
    ssh_user: Optional[str],
    sudo_password: Optional[str]
) -> Dict:
    """
    Choisit la procédure adaptée selon la source :
    - NAS   : export_via_ssh_key
    - Local : export_via_ssh_passwd
    """
    ssh_user = ssh_user or ""
    sudo_password = sudo_password or ""

    ip = source.get("ip", "")
    container = source.get("container", "")

    if _is_local_source(source):
        return export_via_ssh_passwd(ip, ssh_user, sudo_password, container)
    else:
        return export_via_ssh_key(ip, ssh_user, sudo_password, container)
