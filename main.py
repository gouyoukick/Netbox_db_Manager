from backend.csv_utils import load_sources
from backend.export_utils import export_database_with_verification
# from backend.import_utils import import_database  # Pour plus tard

def get_sources():
    """Charge les sources depuis le fichier CSV."""
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CSV_PATH = os.path.join(BASE_DIR, "sources.csv")
    return load_sources(CSV_PATH)

def exporter_netbox(source, ssh_user, sudo_password):
    """
    Effectue l'export d'une base distante avec vérification SHA256.
    """
    return export_database_with_verification(source, ssh_user, sudo_password)

# D'autres fonctions neutres pourront être ajoutées ici (import, copie NAS, etc.)
