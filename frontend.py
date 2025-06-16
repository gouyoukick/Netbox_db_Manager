# === frontend.py ===

import subprocess
import platform
import os

from backend.export_utils import export_database_with_verification
from backend.import_utils import (
    import_database_with_verification,
    verifier_docker_actif,
    creer_dossier_distant,
    copier_fichier_vers_distant,
)
from backend.auth_session import get_ssh_credentials

def afficher_menu_principal():
    print("\n=== Gestion de base de données NetBox ===")
    print("  1 - Exporter une base")
    print("  2 - Importer une base")
    print("  3 - Quitter")

def demander_choix():
    while True:
        try:
            return input("Entrez votre choix (1, 2 ou 3) : ").strip()
        except EOFError:
            print("❌ Erreur d'entrée détectée.")
            return "3"

def afficher_message(message):
    print(message)

def choisir_source(sources):
    print("\nDockers disponibles :")
    print("  0 - Retour au menu précédent")

    for idx, source in enumerate(sources, 1):
        print(f"  {idx} - {source['name']} ({source['ip']}, container: {source['container']})")

    while True:
        try:
            choix = int(input("Choisissez une source (numéro) : "))
            if choix == 0:
                return None
            elif 1 <= choix <= len(sources):
                return sources[choix - 1]
            else:
                print("Numéro invalide.")
        except ValueError:
            print("Veuillez entrer un nombre.")

def tester_connexion_ssh(ip):
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(["ping", param, "1", ip],
                                capture_output=True, timeout=3, stdin=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

def traiter_export(source):
    ssh_user, sudo_password = get_ssh_credentials()
    print(f"\n🔄 Export de la base depuis {source['name']} en cours...")

    result = export_database_with_verification(source, ssh_user, sudo_password)

    if result["status"] == "ok":
        print("✅ Export et copie vérifiés avec succès.")
        print(f"📦 Fichier distant (NAS) : {result['remote_path']}")
        print(f"💾 Fichier local (PC)    : {result['local_path']}")
        print(f"🔐 SHA256 NAS   : {result['hash_remote']}")
        print(f"🔐 SHA256 local : {result['hash_local']}")
    elif result["status"] == "corrupted":
        print("⚠️  La copie du fichier semble corrompue !")
        print(f"🔐 SHA256 NAS   : {result['hash_remote']}")
        print(f"🔐 SHA256 local : {result['hash_local']}")
    else:
        print(f"❌ Erreur lors de l'étape : {result.get('step', 'inconnue')}")
        print(f"🧨 Détail : {result.get('error', 'Pas de message d\'erreur disponible')}")
        if "sudo incorrect" in result.get("error", "").lower():
            print("⛔ Fin du programme pour éviter des tentatives inutiles.")
            exit(1)

def demander_fichier_import():
    chemin_fichier = os.path.join("exported_database", "exported_netbox_database.sql")

    while True:
        print("\n📁 Veuillez placer le fichier de base de données à importer ici :")
        print(f"    ➜ {chemin_fichier}")
        try:
            input("Appuyez sur Entrée une fois le fichier en place...")
        except EOFError:
            print("⛔ Entrée clavier interrompue.")
            return None

        if os.path.isfile(chemin_fichier):
            return chemin_fichier
        else:
            print("❌ Fichier introuvable. Recommencez.")

def traiter_import(sources):
    print("\n=== IMPORT D’UNE BASE NETBOX ===")

    chemin_fichier = demander_fichier_import()
    if not chemin_fichier:
        return

    destination = choisir_source(sources)
    if destination is None:
        print("↩️ Retour au menu principal.")
        return

    print("\n⚠️  ATTENTION : cette opération va écraser la base existante de l’instance suivante :")
    print(f"    ➜ {destination['name']} ({destination['ip']} / {destination['container']})")
    try:
        confirmation = input("Tapez 'oui' pour continuer ou appuyez sur Entrée pour annuler : ").strip().lower()
    except EOFError:
        print("⛔ Entrée clavier interrompue.")
        return

    if confirmation != "oui":
        print("❌ Import annulé.")
        return

    print("✅ Validation reçue.")

    ssh_user, sudo_password = get_ssh_credentials()

    print("🔍 Vérification du container distant...")
    if not verifier_docker_actif(destination["ip"], ssh_user, sudo_password, destination["container"]):
        print(f"❌ Le container {destination['container']} n’est pas actif sur {destination['ip']}.")
        return

    temp_folder = f"/volume1/docker/temp/{destination['container']}"
    print(f"📂 Création du dossier {temp_folder} sur {destination['ip']}")
    if not creer_dossier_distant(destination["ip"], ssh_user, sudo_password, temp_folder):
        print("❌ Erreur à la création du dossier distant.")
        return

    fichier_distant = f"{temp_folder}/import.sql"
    print(f"📤 Copie du fichier SQL vers : {fichier_distant}")
    if not copier_fichier_vers_distant(chemin_fichier, ssh_user, destination["ip"], fichier_distant):
        print("❌ Échec de la copie du fichier SQL.")
        return

    print("✅ Fichier copié avec succès.")
