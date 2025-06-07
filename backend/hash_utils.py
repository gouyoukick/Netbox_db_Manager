import hashlib

def compute_sha256(file_path):
    """
    Calcule l'empreinte SHA256 d'un fichier.
    :param file_path: Chemin absolu vers le fichier.
    :return: Hexdigest SHA256 du fichier.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return None


def compare_sha256(file_path1, file_path2):
    """
    Compare les SHA256 de deux fichiers.
    :param file_path1: Chemin vers le premier fichier.
    :param file_path2: Chemin vers le second fichier.
    :return: Tuple (identiques: bool, hash1: str, hash2: str)
    """
    hash1 = compute_sha256(file_path1)
    hash2 = compute_sha256(file_path2)

    if hash1 is None or hash2 is None:
        return False, hash1, hash2

    return hash1 == hash2, hash1, hash2
