from frontend import (
    afficher_menu_principal,
    demander_choix,
    afficher_message,
    choisir_source,
    tester_connexion_ssh,
    traiter_export,
    traiter_import
)
from main import get_sources
from backend.export_utils import verifier_sudo_password
from backend.auth_session import get_ssh_credentials

# titre et version logiciel
titre = "Network_db_Manager: v 0.5"
print("#" * len(titre))
print(titre)
print("#" * len(titre))


def main():
    sources = get_sources()
    if not sources:
        afficher_message("❌ Aucune source détectée dans sources.csv")
        return

    while True:
        afficher_menu_principal()
        choix = demander_choix()

        if choix == "1":
            if not sources:
                afficher_message("Aucune source disponible pour l'export.")
                continue

            source_choisie = choisir_source(sources)
            if source_choisie is None:
                continue

            if not tester_connexion_ssh(source_choisie["ip"]):
                afficher_message("❌ Netbox Source non joignable : vérifiez l'adresse IP ou la connexion réseau.")
                continue

            ssh_user, sudo_password = get_ssh_credentials()

            if not verifier_sudo_password(ssh_user, sudo_password, source_choisie["ip"]):
                afficher_message("⛔ Mot de passe sudo invalide (sur la machine distante). Fin du programme.")
                return

            afficher_message("⚠️  ATTENTION : Ne modifiez pas l'interface NetBox pendant l'export !")
            try:
                input("Appuyez sur Entrée pour continuer...")
            except EOFError:
                afficher_message("⛔ Entrée clavier interrompue.")
                continue

            traiter_export(source_choisie)

        elif choix == "2":
            traiter_import(sources)

        elif choix == "3":
            afficher_message("Au revoir !")
            break


if __name__ == "__main__":
    main()
