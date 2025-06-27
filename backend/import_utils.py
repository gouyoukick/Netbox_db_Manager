import subprocess
from pathlib import Path

GIT_SSH = r"C:/Program Files/Git/usr/bin/ssh.exe"
SSH_KEY = str(Path.home() / ".ssh" / "id_rsa")


def import_database_with_verification(source, ssh_user, sudo_password):
    project_root = Path(__file__).resolve().parent.parent
    sql_file = project_root / 'exported_database' / 'exported_netbox_database.sql'

    if not sql_file.exists():
        return {'status': 'error', 'step': 'file_not_found', 'message': f'Fichier introuvable : {sql_file}'}

    is_local = _is_local_source(source)

    status = _verify_container(source, ssh_user, sudo_password, is_local)
    if status['status'] != 'ok':
        return status

    status = _prepare_temp_dir(source, ssh_user, is_local)
    if status['status'] != 'ok':
        return status

    status = _copy_sql_file(source, ssh_user, sql_file, is_local)
    if status['status'] != 'ok':
        return status

    ip = source.get('ip')
    container = source.get('container')
    delete_result = delete_database(ip, container, ssh_user, sudo_password, is_local)
    if delete_result.get('status') != 'ok':
        return delete_result

    push_result = push_new_database(ip, container, ssh_user, sudo_password, is_local)
    if push_result.get('status') != 'ok':
        return push_result

    return {'status': 'ok', 'step': 'all_done', 'message': 'Import prêt.'}



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
    if is_local:
        # Dossier dédié au serveur local
        cmd = "mkdir -p ~/temp/netbox-postgres/"
    else:
        remote_path = f"~/temp/{container}"
        cmd = f"mkdir -p {remote_path}"

    ssh_cmd = [GIT_SSH, "-i", SSH_KEY, f"{ssh_user}@{ip}", cmd]
    proc = subprocess.run(ssh_cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        return {"status": "error", "step": "prepare_temp_dir", "message": proc.stderr.strip()}

    return {"status": "ok", "step": "prepare_temp_dir"}

def _copy_sql_file(source, ssh_user, local_path, is_local):
    ip = source['ip']
    container = source['container'].strip()
    if is_local:
        # Utilisation de scp via Git Bash pour le serveur local
        project_root = Path(__file__).resolve().parent.parent
        local_sql_path = project_root / 'exported_database' / 'exported_netbox_database.sql'
        # Passe en style POSIX pour Git Bash (/c/Users/...)
        local_posix = local_sql_path.as_posix().replace('C:', '/c')
        remote = '~/temp/netbox-postgres/import.sql'
        bash_exe = r'C:\Program Files\Git\bin\bash.exe'
        # Hardcode le nom du fichier dans le chemin POSIX, sans option -i pour scp
        cmd = f"\"{bash_exe}\" -lc 'scp {local_posix} {ssh_user}@{ip}:{remote}'"
        print('DEBUG scp CMD:', cmd)
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            return {'status': 'error', 'step': 'copy_sql', 'message': proc.stderr.strip()}
        return {'status': 'ok', 'step': 'copy_sql'}
    else:
        # NAS Synology inchangé
        remote_path = f"~/temp/{container}/import.sql"
        local_path_unix = str(local_path).replace('\\', '/').replace('C:', '/c')
        ssh_key_unix = SSH_KEY.replace('\\', '/').replace('C:', '/c')
        bash_exe = r"C:\Program Files\Git\bin\bash.exe"
        ssh_exe = r"C:\Program Files\Git\usr\bin\ssh.exe"
        cmd = (
            f"\"{bash_exe}\" -c 'cat \"{local_path_unix}\" | \"{ssh_exe}\" -i \"{ssh_key_unix}\" {ssh_user}@{ip} \"cat > {remote_path}\"'"
        )
        print("DEBUG CMD:", cmd)
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            return {'status': 'error', 'step': 'copy_sql', 'message': proc.stderr.strip()}
        return {'status': 'ok', 'step': 'copy_sql'}


def delete_database(ip: str, container: str, ssh_user: str, sudo_password: str, is_local: bool):
    # Choix du binaire docker selon la destination
    docker_bin = 'docker' if is_local else '/usr/local/bin/docker'
    # Commande pour supprimer et recréer le schéma public
    sql_cmd = (
        'psql -U netbox-user -d netbox '
        '-c "DROP SCHEMA public CASCADE;" '
        '-c "CREATE SCHEMA public;"'
    )
    remote = f"echo '{sudo_password}' | sudo -S {docker_bin} exec -i {container} sh -c '{sql_cmd}'"
    ssh_cmd = [GIT_SSH, '-i', SSH_KEY, f"{ssh_user}@{ip}", remote]
    proc = subprocess.run(ssh_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {'status': 'error', 'step': 'delete_database', 'message': proc.stderr.strip()}
    return {'status': 'ok', 'step': 'delete_database'}


def push_new_database(ip: str, container: str, ssh_user: str, sudo_password: str, is_local: bool):
    """
    Importe un dump SQL dans la base NetBox.
    Reproduce la commande Git Bash en SSH :
      sudo docker exec -i <container> psql -U netbox-user -d netbox < <fichier>
    Affiche la progression en direct.
    """
    try:
        # Choix du chemin d'import sur l'hôte distant
        if not is_local:
            # NAS Synology
            base_dir = "/volume1/homes/gravity/temp"
            docker_bin = "/usr/local/bin/docker"
        else:
            # Serveur local
            base_dir = "/home/gravity/temp"
            docker_bin = "docker"
        remote_file = f"{base_dir}/{container}/import.sql"

        # Construction de la commande distante : pipe du mot de passe dans sudo, redirection locale par sh -c
        remote_cmd = (
            f"echo '{sudo_password}' | sudo -S sh -c '"  
            f"{docker_bin} exec -i {container} psql -U netbox-user -d netbox < {remote_file}'"
        )

        # Appel SSH avec pseudo-tty pour affichage en direct
        ssh_cmd = [
            GIT_SSH,
            "-t",
            "-i", SSH_KEY,
            f"{ssh_user}@{ip}",
            remote_cmd
        ]

        # Debug: commande complète
        print("DEBUG push_new_database SSH CMD:", ssh_cmd)

        # Exécution bloquante, affiche stdout/stderr en direct
        proc = subprocess.run(ssh_cmd, text=True)

        if proc.returncode != 0:
            print("echec import db")
            return {"status": "error", "step": "push_new_database", "message": f"Return code {proc.returncode}"}

        print("OK import db")
        return {"status": "ok", "step": "push_new_database"}

    except Exception as e:
        print("DEBUG push_new_database exception:", str(e))
        print("echec import db")
        return {"status": "error", "step": "push_new_database", "message": str(e)}
