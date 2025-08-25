import os
import yaml


def load_config(config_path="config.yaml"):
    """
    Charge et retourne le contenu du fichier de configuration YAML.

    Args:
        config_path (str): Chemin vers le fichier YAML.

    Returns:
        dict: Configuration chargée.

    Raises:
        FileNotFoundError: Si le fichier n'existe pas.
        yaml.YAMLError: Si le fichier contient une erreur de syntaxe.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ Fichier de configuration non trouvé : {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        try:
            return yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"❌ Erreur lors du parsing YAML : {e}")
