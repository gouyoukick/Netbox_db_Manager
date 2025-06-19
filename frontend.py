# === frontend.py ===

import os
from pathlib import Path
import getpass
import subprocess

from backend.import_utils import import_database_with_verification
from backend.export_utils import export_database_with_verification
from backend.auth_session import (
    is_ssh_credentials_set,
    set_ssh_credentials,
    get_ssh_credentials
)

# Chemin fixe pour le SQL exporté
EXPORT_PATH = Path("exported_database") / "exported_netbox_database.sql"


def afficher_menu_principal():
    print("\n=== Gestion de base de données NetBox ===")
    print("  1 - Exporter une base")
    print("  2 - Importer une base")
    print("  3 - Quitter")


def demander_choix():
    return input("Entrez votre choix (1, 2 ou 3) : ")


def afficher_message(msg):
    print(f"\n{msg}")


def demander_utilisateur(message):
    try:
        return input(message)
    except KeyboardInterrupt:
        print("\nInterruption utilisateur.")
        return ""


def choisir_source(sources):
    print("\nDockers disponibles :")
    for i, src in enumerate(sources):
        print(f"  {i+1} - {src['name']} ({src['ip']}, container: {src['container']})")
    print("  0 - Retour au menu précédent")

    choix = input("Choisissez une source (numéro) : ")
    if not choix.isdigit():
        return None
    index = int(choix)
    if index == 0 or index < 1 or index > len(sources):
        return None
    return sources[index - 1]


def tester_connexion_ssh(ip):
    param = "-n" if os.name == "nt" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False


def obtenir_ssh_credentials():
    if not is_ssh_credentials_set():
        ssh_user = input("Entrez le nom d’utilisateur SSH : ").strip()
        sudo_password = getpass.getpass("Entrez le mot de passe sudo : ")
        set_ssh_credentials(ssh_user, sudo_password)
    return get_ssh_credentials()


def traiter_export(source):
    ssh_user, sudo_password = obtenir_ssh_credentials()
    if not ssh_user or not sudo_password:
        print("❌ Identifiants SSH ou mot de passe sudo manquants.")
        return

    result = export_database_with_verification(source, ssh_user, sudo_password)

    if result.get("status") == "error":
        print("❌ Erreur durant l’export de la base.")
        print(f"🧨 Détail : {result.get('message', 'Erreur inconnue')}")
        return

    if result.get("status") == "corrupted":
        print("⚠️  La copie du fichier semble corrompue !")
        print(f"🔐 SHA256 NAS   : {result['hash_remote']}")
        print(f"🔐 SHA256 local : {result['hash_local']}")
        return

    print("✅ Export et copie vérifiés avec succès.")
    print(f"📦 Fichier distant (NAS) : {result['remote_path']}")
    print(f"💾 Fichier local (PC)    : {result['local_path']}")
    print(f"🔐 SHA256 NAS   : {result['hash_remote']}")
    print(f"🔐 SHA256 local : {result['hash_local']}")


def traiter_import(sources):
    print("\n=== IMPORT D’UNE BASE NETBOX ===")
    print("\n📁 Le fichier à importer doit être présent ici :")
    print(f"    ➜ {EXPORT_PATH}")
    input("Appuyez sur Entrée une fois le fichier en place...")

    if not EXPORT_PATH.exists():
        print("❌ Le fichier à importer est introuvable. Veuillez réessayer.")
        return

    print("\nDockers disponibles :")
    for i, src in enumerate(sources):
        print(f"  {i} - {src['name']} ({src['ip']}, container: {src['container']})")

    choix = input("Choisissez une source (numéro) : ")
    if not choix.isdigit() or int(choix) < 0 or int(choix) >= len(sources):
        print("❌ Choix invalide.")
        return

    destination = sources[int(choix)]

    print("\n⚠️  ATTENTION : cette opération va écraser la base existante de l’instance suivante :")
    print(f"    ➜ {destination['name']} ({destination['ip']} / {destination['container']})")
    confirmation = input("Tapez 'oui' pour continuer ou appuyez sur Entrée pour annuler : ")
    if confirmation.strip().lower() != "oui":
        print("❌ Opération annulée.")
        return

    ssh_user, sudo_password = obtenir_ssh_credentials()
    result = import_database_with_verification(destination, ssh_user, sudo_password)

    if result.get("status") == "error":
        print("❌ Erreur durant l’import de la base.")
        print(f"🧨 Détail : {result.get('message', 'Erreur inconnue')}")
        return

    print("✅ Import prêt !")
    print(f"✔ Étape : {result.get('step')} | Message : {result.get('message')} ")
