# signals/validate_config.py

import sys
from loaders.config_loader import validate_config
from loaders.config_validator import validate_config_values

def main():
    print("🔍 Validation de la configuration en cours...")

    try:
        # Vérifie structure et types
        validate_config_values()
        # Vérifie existence des fichiers
        validate_config()
    except Exception as e:
        print(f"❌ Validation échouée : {e}")
        sys.exit(1)

    print("✅ Configuration valide et prête à l'emploi.")

if __name__ == "__main__":
    main()
