from frontend import (
    afficher_menu_principal,
    demander_choix,
    demander_mot_de_passe,
    afficher_message,
    choisir_source,
    tester_connexion_ssh,
    traiter_export,
    demander_login
)
from main import get_sources
from backend.export_utils import verifier_sudo_password


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

            # 🔐 Demande du login et mot de passe APRES le choix de la source
            login_ssh = demander_login()
            mot_de_passe_sudo = demander_mot_de_passe()

            # ✅ Test du mot de passe sudo sur la bonne IP
            if not verifier_sudo_password(login_ssh, mot_de_passe_sudo, source_choisie["ip"]):
                afficher_message("⛔ Mot de passe sudo invalide (sur la machine distante). Fin du programme.")
                return

            afficher_message("⚠️  ATTENTION : Ne modifiez pas l'interface NetBox pendant l'export !")
            try:
                input("Appuyez sur Entrée pour continuer...")
            except EOFError:
                afficher_message("⛔ Entrée clavier interrompue.")
                continue

            # ✅ Export exécuté
            traiter_export(source_choisie, login_ssh, mot_de_passe_sudo)

        elif choix == "2":
            afficher_message("Fonction d'import non encore disponible.")

        elif choix == "3":
            afficher_message("Au revoir !")
            break


if __name__ == "__main__":
    main()
