# === export_utils.py ===

import subprocess
import os
from pathlib import Path
import shutil
from backend.hash_utils import compute_sha256

def verifier_sudo_password(ssh_user, sudo_password, remote_ip):
    ssh_key_path = str(Path.home() / ".ssh" / "id_rsa")
    GIT_SSH = "C:/Program Files/Git/usr/bin/ssh.exe"

    test_cmd = f"echo '{sudo_password}' | sudo -S true"
    result = subprocess.run(
        [GIT_SSH, "-i", ssh_key_path, f"{ssh_user}@{remote_ip}", test_cmd],
        capture_output=True,
        text=True
    )

    return result.returncode == 0 and "sorry" not in result.stderr.lower()

def export_database_with_verification(source: dict, ssh_user: str, sudo_password: str) -> dict:
    ip = source["ip"]
    container_name = source["container"]

    ssh_key_path = str(Path.home() / ".ssh" / "id_rsa")
    GIT_SSH = "C:/Program Files/Git/usr/bin/ssh.exe"

    remote_container_path = f"/tmp/exported_netbox_database.sql"
    remote_sql_path = f"/tmp/{container_name}_exported_netbox_database.sql"

    # === Étape 1 : pg_dump ===
    dump_cmd = (
        f"echo '{sudo_password}' | sudo -S /usr/local/bin/docker exec {container_name} "
        f"pg_dump -U netbox-user netbox -f {remote_container_path}"
    )
    dump_result = subprocess.run([GIT_SSH, "-i", ssh_key_path, f"{ssh_user}@{ip}", dump_cmd], capture_output=True, text=True)
    if dump_result.returncode != 0:
        if "incorrect password" in dump_result.stderr.lower() or "sorry" in dump_result.stderr.lower():
            return {
                "status": "error",
                "step": "pg_dump_remote",
                "error": "Mot de passe sudo incorrect"
            }
        return {
            "status": "error",
            "step": "pg_dump_remote",
            "error": dump_result.stderr.strip()
        }

    # === Étape 2 : docker cp ===
    copy_out_cmd = (
        f"echo '{sudo_password}' | sudo -S /usr/local/bin/docker cp "
        f"{container_name}:{remote_container_path} {remote_sql_path}"
    )
    copy_result = subprocess.run([GIT_SSH, "-i", ssh_key_path, f"{ssh_user}@{ip}", copy_out_cmd], capture_output=True, text=True)
    if copy_result.returncode != 0:
        if "incorrect password" in copy_result.stderr.lower() or "sorry" in copy_result.stderr.lower():
            return {
                "status": "error",
                "step": "docker_cp_out",
                "error": "Mot de passe sudo incorrect"
            }
        return {
            "status": "error",
            "step": "docker_cp_out",
            "error": copy_result.stderr.strip()
        }

    # === Étape 3 : SHA256 distant ===
    hash_remote_cmd = f"sha256sum {remote_sql_path}"
    hash_result = subprocess.run([GIT_SSH, "-i", ssh_key_path, f"{ssh_user}@{ip}", hash_remote_cmd], capture_output=True, text=True)
    if hash_result.returncode != 0:
        return {
            "status": "error",
            "step": "sha256_remote",
            "error": hash_result.stderr.strip()
        }

    try:
        hash_remote = hash_result.stdout.split()[0].strip()
    except Exception:
        return {
            "status": "error",
            "step": "parse_sha256_remote",
            "error": f"Sortie inattendue : {hash_result.stdout.strip()}"
        }

    # === Étape 4 : Récupération locale ===
    local_dir = Path("exported_database")
    local_dir.mkdir(parents=True, exist_ok=True)
    local_sql_path = local_dir / "exported_netbox_database.sql"

    fetch_cmd = [GIT_SSH, "-i", ssh_key_path, f"{ssh_user}@{ip}", f"cat {remote_sql_path}"]
    try:
        with open(local_sql_path, "wb") as f_out:
            fetch_result = subprocess.run(fetch_cmd, stdout=f_out, stderr=subprocess.PIPE)
        if fetch_result.returncode != 0:
            return {
                "status": "error",
                "step": "scp_transfer",
                "error": fetch_result.stderr.decode().strip()
            }
    except Exception as e:
        return {
            "status": "error",
            "step": "scp_transfer",
            "error": str(e)
        }

    # === Étape 5 : SHA256 local et comparaison ===
    temp_copy_path = local_sql_path.parent / f"temp_copy_{container_name}.sql"
    shutil.copy(local_sql_path, temp_copy_path)
    hash_local = compute_sha256(temp_copy_path)
    temp_copy_path.unlink(missing_ok=True)

    return {
        "status": "ok" if hash_local == hash_remote else "corrupted",
        "step": "compare_sha256",
        "remote_path": remote_sql_path,
        "local_path": str(local_sql_path),
        "hash_remote": hash_remote,
        "hash_local": hash_local
    }
