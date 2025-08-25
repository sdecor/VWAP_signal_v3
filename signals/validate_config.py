# signals/validate_config.py

import sys
from signals.loaders.config_loader import validate_config
from signals.loaders.config_validator import validate_config_values

def main():
    print("🔍 Validation de la configuration en cours...")

    try:
        validate_config_values()  # structure/types/valeurs
        validate_config()         # existence des fichiers
    except Exception as e:
        print(f"❌ Validation échouée : {e}")
        sys.exit(1)

    print("✅ Configuration valide et prête à l'emploi.")

if __name__ == "__main__":
    main()
