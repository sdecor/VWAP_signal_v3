import os
import importlib.util
import inspect
from typing import List, Optional

# On utilise ton lecteur existant
try:
    from signals.utils.config_reader import load_config  # si ton projet est packagé
except Exception:
    # fallback si l'import relatif n'est pas dispo pendant des tests
    import yaml
    def load_config(config_path: str = "config.yaml"):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"❌ Fichier de configuration non trouvé : {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


def discover_signal_modules(directory: str) -> List[str]:
    """Découvre les modules de signal dans un répertoire donné."""
    modules = []
    if not os.path.isdir(directory):
        print(f"⚠️  Répertoire de règles introuvable : {directory}")
        return modules
    for filename in os.listdir(directory):
        if filename.endswith(".py") and not filename.startswith("__"):
            modules.append(os.path.join(directory, filename))
    return modules


def load_module_from_path(path: str):
    """Charge dynamiquement un module à partir d'un chemin de fichier."""
    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None  # pour mypy/pyright
    spec.loader.exec_module(module)
    return module


def _apply_with_optional_config(module, config, *args, **kwargs):
    """
    Appelle module.apply() en passant `config` uniquement si la signature l'accepte.
    """
    func = getattr(module, "apply", None)
    if func is None:
        print(f"⚠️  Module {module.__name__} ne contient pas de fonction 'apply'.")
        return

    try:
        sig = inspect.signature(func)
        if "config" in sig.parameters:
            return func(config=config, *args, **kwargs)
        else:
            return func(*args, **kwargs)
    except TypeError:
        # Si la signature est exotique (ex: C-extension) on essaye sans config
        return func(*args, **kwargs)


def run_all_signals(directory: str, config: Optional[dict] = None, *args, **kwargs):
    """
    Exécute la fonction `apply` de chaque module de signal dans le dossier spécifié.
    - Passe `config` seulement si la fonction l'accepte.
    - Continue même si un module échoue.
    """
    if config is None:
        try:
            config = load_config()
        except Exception as e:
            print(f"❌ Impossible de charger config.yaml : {e}")
            config = None  # on continue, les règles qui n’en ont pas besoin fonctionneront

    modules_paths = discover_signal_modules(directory)
    for path in modules_paths:
        try:
            module = load_module_from_path(path)
        except Exception as e:
            print(f"❌ Échec de chargement du module {os.path.basename(path)} : {e}")
            continue

        print(f"▶️  Exécution de : {os.path.basename(path)}")
        try:
            _apply_with_optional_config(module, config, *args, **kwargs)
        except Exception as e:
            print(f"❌ Erreur durant l'exécution de {os.path.basename(path)} : {e}")


if __name__ == "__main__":
    run_all_signals("rules")  # comportement identique à avant
