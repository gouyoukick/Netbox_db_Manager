# === backend/csv_utils.py ===
import csv
from pathlib import Path

def load_sources(fichier_csv):
    sources = []
    fichier_path = Path(fichier_csv)

    if not fichier_path.exists():
        return []  # Pas d'affichage ici : la gestion est déléguée au frontend

    with open(fichier_csv, newline='', encoding='utf-8') as csvfile:
        sample = csvfile.read(1024)
        csvfile.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except csv.Error:
            dialect = csv.excel  # fallback à la virgule

        reader = csv.DictReader(csvfile, dialect=dialect)
        for row in reader:
            if {"name", "ip", "container"} <= row.keys():
                sources.append({
                    "name": row["name"].strip(),
                    "ip": row["ip"].strip(),
                    "container": row["container"].strip()
                })

    return sources
