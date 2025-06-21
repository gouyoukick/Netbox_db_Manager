import subprocess
from pathlib import Path

GIT_SSH = r"C:/Program Files/Git/usr/bin/ssh.exe"
SSH_KEY = str(Path.home() / ".ssh" / "id_rsa")


def import_database_with_verification(source, ssh_user, sudo_password):
    project_root = Path(__file__).resolve().parent.parent
    sql_file = project_root / "exported_database" / "exported_netbox_database.sql"

    if not sql_file.exists():
        return {"status": "error", "step": "file_not_found", "message": f"Fichier introuvable : {sql_file}"}

    is_local = _is_local_source(source)

    # Vérification du container
    status = _verify_container(source, ssh_user, sudo_password, is_local)
    if status["status"] != "ok":
        return status

    # Préparation du répertoire temporaire
    status = _prepare_temp_dir(source, ssh_user, is_local)
    if status["status"] != "ok":
        return status

    # Copie du SQL sur la destination
    status = _copy_sql_file(source, ssh_user, sql_file, is_local)
    if status["status"] != "ok":
        return status

    # Suppression du schéma public de la base
    ip = source.get("ip")
    container = source.get("container")
    delete_result = delete_database(ip, container, ssh_user, sudo_password)
    if delete_result.get("status") != "ok":
        return delete_result

    # Import du nouveau dump SQL
    push_result = push_new_database(ip, container, ssh_user, sudo_password, is_local)
    if push_result.get("status") != "ok":
        return push_result

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
    """
    Copie le fichier SQL local vers la destination via un pipe SSH en utilisant Git Bash.
    """
    ip = source["ip"]
    container = source["container"].strip()
    remote_path = f"~/temp/{container}/import.sql"

    # Convertit les chemins Windows en format Unix pour Git Bash
    local_path_unix = str(local_path).replace('\\\\', '/').replace('C:', '/c')
    ssh_key_unix = SSH_KEY.replace('\\\\', '/').replace('C:', '/c')

    bash_exe = r"C:\\Program Files\\Git\\bin\\bash.exe"
    ssh_exe = r"C:\\Program Files\\Git\\usr\\bin\\ssh.exe"

    # Construction de la commande : on encadre l'ensemble du -c entre guillemets simples
    cmd = (
        f"\"{bash_exe}\" -c 'cat \"{local_path_unix}\" | \"{ssh_exe}\" -i \"{ssh_key_unix}\" {ssh_user}@{ip} \"cat > {remote_path}\"'"
    )
    # Affiche la commande brute pour debug
    print("DEBUG CMD:", cmd)

    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if proc.returncode != 0:
        return {"status": "error", "step": "copy_sql", "message": proc.stderr.strip()}

    return {"status": "ok", "step": "copy_sql"}

def delete_database(ip: str, container: str, ssh_user: str, sudo_password: str):
    """
    Supprime le schéma public de la base NetBox et le recrée.
    Utilise docker exec avec deux -c pour psql, évitant les problèmes de quoting.
    Retourne un dict avec le statut et le message.
    """
    try:
        # Prépare la commande psql en deux -c
        sql_cmd = (
            "psql -U netbox-user -d netbox "
            "-c \"DROP SCHEMA public CASCADE;\" "
            "-c \"CREATE SCHEMA public;\""
        )
        # Chemin absolu du binaire docker sur l'hôte distant
        docker_bin = "/usr/local/bin/docker"
        # Construit la commande distante avec pipe du mot de passe sudo
        remote = (
            f"echo '{sudo_password}' | sudo -S {docker_bin} exec -i {container} sh -c '{sql_cmd}'"
        )
        # Prépare l'appel SSH
        ssh_cmd = [
            GIT_SSH,
            "-i", SSH_KEY,
            f"{ssh_user}@{ip}",
            remote
        ]

        # Debug: afficher la commande SSH complète
        print("DEBUG delete_database SSH CMD:", ssh_cmd)

        proc = subprocess.run(ssh_cmd, capture_output=True, text=True)
        print("DEBUG delete_database stdout:", proc.stdout)
        print("DEBUG delete_database stderr:", proc.stderr)

        if proc.returncode != 0:
            print("echec suppression db")
            return {"status": "error", "step": "delete_database", "message": proc.stderr.strip()}

        print("OK suppression db")
        return {"status": "ok", "step": "delete_database"}
    except Exception as e:
        print("DEBUG delete_database exception:", str(e))
        print("echec suppression db")
        return {"status": "error", "step": "delete_database", "message": str(e)}


def push_new_database(ip: str, container: str, ssh_user: str, sudo_password: str, is_local: bool):
    """
    Importe un dump SQL dans la base NetBox.
    Retourne un dict avec le statut et le message.
    """
    try:
        # Détermine le chemin du fichier SQL à importer
        if is_local:
            import_path = f"/volume1/homes/gravity/temp/{container}/import.sql"
        else:
            import_path = f"~/temp/{container}/import.sql"
        cmd = (
            f'"{GIT_SSH}" -i "{SSH_KEY}" {ssh_user}@{ip} '
            f'"sudo docker exec -i {container} psql -U netbox-user -d netbox < {import_path}"'
        )
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        # Debug output
        print("DEBUG push_new_database stdout:", proc.stdout)
        print("DEBUG push_new_database stderr:", proc.stderr)
        if proc.returncode != 0:
            print("echec import db")
            return {"status": "error", "step": "push_new_database", "message": proc.stderr.strip()}
        print("OK import db")
        return {"status": "ok", "step": "push_new_database"}
    except Exception as e:
        print("DEBUG push_new_database exception:", str(e))
        print("echec import db")
        return {"status": "error", "step": "push_new_database", "message": str(e)}
