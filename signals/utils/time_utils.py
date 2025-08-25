# time_utils.py

def get_current_hour_label(current_hour: int, config_by_label: dict) -> str | None:
    """
    Retourne le label de session (ex: 'LONDON_AM') correspondant à l'heure courante.

    Args:
        current_hour (int): Heure courante (0–23)
        config_by_label (dict): Dictionnaire des configurations optimales (clé = label)

    Returns:
        str | None: Le label de session correspondant, ou None si aucune session active
    """
    for label, cfg in config_by_label.items():
        h_start = cfg.get("heure_debut")
        h_end = cfg.get("heure_fin")

        if h_start is None or h_end is None:
            continue

        if h_start <= current_hour < h_end:
            return label

    return None
