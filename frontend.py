import getpass
import subprocess
import platform
from backend.export_utils import export_database_with_verification


def afficher_menu_principal():
    print("\n=== Gestion de base de données NetBox ===")
    print("  1 - Exporter une base")
    print("  2 - Importer une base (non disponible)")
    print("  3 - Quitter")


def demander_choix():
    while True:
        try:
            return input("Entrez votre choix (1, 2 ou 3) : ").strip()
        except EOFError:
            print("❌ Erreur d'entrée détectée.")
            return "3"


def demander_login():
    return input("Entrez le nom d’utilisateur : ").strip()


def demander_mot_de_passe():
    return getpass.getpass("Entrez le mot de passe : ")


def afficher_message(message):
    print(message)


def choisir_source(sources):
    print("\nSources disponibles :")
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


def traiter_export(source, ssh_user, sudo_password):
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
