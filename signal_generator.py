import os
import importlib.util
from typing import List


def discover_signal_modules(directory: str) -> List[str]:
    """Découvre les modules de signal dans un répertoire donné."""
    modules = []
    for filename in os.listdir(directory):
        if filename.endswith(".py") and not filename.startswith("__"):
            modules.append(os.path.join(directory, filename))
    return modules


def load_module_from_path(path: str):
    """Charge dynamiquement un module à partir d'un chemin de fichier."""
    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_all_signals(directory: str, *args, **kwargs):
    """Exécute la fonction `apply` de chaque module de signal dans le dossier spécifié."""
    modules_paths = discover_signal_modules(directory)
    for path in modules_paths:
        module = load_module_from_path(path)
        if hasattr(module, "apply"):
            print(f"▶️  Exécution de : {os.path.basename(path)}")
            module.apply(*args, **kwargs)
        else:
            print(f"⚠️  Module {path} ne contient pas de fonction 'apply'.")


if __name__ == "__main__":
    run_all_signals("rules")  # Exemple d’appel (à adapter)
