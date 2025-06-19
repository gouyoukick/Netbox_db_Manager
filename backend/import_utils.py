import subprocess
from pathlib import Path

GIT_SSH = "C:/Program Files/Git/usr/bin/ssh.exe"
SSH_KEY = str(Path.home() / ".ssh" / "id_rsa")

def import_database_with_verification(source, ssh_user, sudo_password):
    project_root = Path(__file__).resolve().parent.parent
    sql_file = project_root / "exported_database" / "exported_netbox_database.sql"

    if not sql_file.exists():
        return {"status": "error", "step": "file_not_found", "message": f"Fichier introuvable : {sql_file}"}

    is_local = _is_local_source(source)

    status = _verify_container(source, ssh_user, sudo_password, is_local)
    if status["status"] != "ok":
        return status

    status = _prepare_temp_dir(source, ssh_user, is_local)
    if status["status"] != "ok":
        return status

    status = _copy_sql_file(source, ssh_user, sql_file, is_local)
    if status["status"] != "ok":
        return status

    return {"status": "ok", "step": "all_done", "message": "Import prêt."}


def _is_local_source(source):
    name = source.get("name", "")
    ip = source.get("ip", "")
    return "local" in name.lower() or ip.startswith("10.")


def _verify_container(source, ssh_user, sudo_password, is_local):
    ip = source["ip"]
    container = source["container"]

    docker_cmd = "/usr/local/bin/docker" if not is_local else "docker"
    cmd = f"echo '{sudo_password}' | sudo -S {docker_cmd} inspect -f '{{{{.State.Running}}}}' {container}"

    ssh_cmd = [GIT_SSH, "-i", SSH_KEY, f"{ssh_user}@{ip}", cmd]

    proc = subprocess.run(ssh_cmd, capture_output=True, text=True)

    if proc.returncode != 0 or proc.stdout.strip().lower() != "true":
        return {"status": "error", "step": "docker_check", "message": proc.stderr.strip()}

    return {"status": "ok", "step": "docker_check"}


def _prepare_temp_dir(source, ssh_user, is_local):
    ip = source["ip"]
    container = source["container"]
    remote_path = f"~/temp/{container}"

    cmd = f"mkdir -p {remote_path}"

    ssh_cmd = [GIT_SSH, "-i", SSH_KEY, f"{ssh_user}@{ip}", cmd]

    proc = subprocess.run(ssh_cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        return {"status": "error", "step": "prepare_temp_dir", "message": proc.stderr.strip()}

    return {"status": "ok", "step": "prepare_temp_dir"}


def _copy_sql_file(source, ssh_user, local_path, is_local):
    ip = source["ip"]
    container = source["container"]
    remote_path = f"~/temp/{container}/import.sql"

    local_path_unix = str(local_path).replace('\\', '/').replace('C:', '/c')
    ssh_key_unix = SSH_KEY.replace('\\', '/').replace('C:', '/c')

    bash_exe = r"C:\Program Files\Git\bin\bash.exe"
    ssh_exe = r"C:\Program Files\Git\usr\bin\ssh.exe"

    cmd = (
        f'"{bash_exe}" -c "cat \\"{local_path_unix}\\" | '
        f'\\"{ssh_exe}\\" -i \\"{ssh_key_unix}\\" {ssh_user}@{ip} '
        f'\'cat > {remote_path}\'"'
    )

    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if proc.returncode != 0:
        return {"status": "error", "step": "copy_sql", "message": proc.stderr.strip()}

    return {"status": "ok", "step": "copy_sql"}
