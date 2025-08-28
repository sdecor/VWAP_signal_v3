#!/usr/bin/env python3
"""
Start Trading Runner

- Valide la configuration (valeurs + fichiers)
- Lance la boucle temps réel qui surveille le CSV 5m
- Déclenche trade_decider + envoi d'ordre (dry-run ou live selon config.yaml)

Usage:
  python start_trading.py
  python start_trading.py --validate-only
  python start_trading.py --skip-validate
"""

import argparse
import sys
import os
# start_trading.py (ajouter au tout début du fichier)

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("trading.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def main():
    # S'assure que la racine est dans le PYTHONPATH
    root = os.path.abspath(os.path.dirname(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)

    parser = argparse.ArgumentParser(description="VWAP_SIGNAL_V3 - Start trading loop")
    parser.add_argument("--validate-only", action="store_true", help="Valide la config et stoppe.")
    parser.add_argument("--skip-validate", action="store_true", help="Ne pas valider avant de lancer.")
    args = parser.parse_args()

    # Imports tardifs après ajustement du PYTHONPATH
    from signals.loaders.config_loader import validate_config
    from signals.loaders.config_validator import validate_config_values
    from signals.runner.live_loop import run_live_loop

    if not args.skip_validate:
        print("🔍 Validation de la configuration...")
        # 1) Clés/valeurs/types
        validate_config_values()
        # 2) Existence des fichiers
        validate_config()
        print("✅ Configuration OK.")

    if args.validate_only:
        print("🛑 Mode --validate-only : arrêt après validation.")
        return

    print("🚀 Démarrage de la boucle live…")
    run_live_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur.")
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        sys.exit(1)
