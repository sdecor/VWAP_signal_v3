# main.py

import sys
from utils.config_reader import load_config

def main():
    config = load_config("config.yaml")
    commands = config.get("commands", {})

    if len(sys.argv) < 2:
        print("❌ Commande manquante. Exemple : python main.py search <args>")
        return

    command = sys.argv[1]
    if command not in commands:
        print(f"❌ Commande inconnue : {command}")
        print("📋 Commandes disponibles :", ", ".join(commands.keys()))
        return

    module_path = commands[command]
    try:
        mod = __import__(module_path, fromlist=["run"])
    except ImportError as e:
        print(f"❌ Erreur d'import du module '{module_path}' : {e}")
        return

    from api.client import APIClient
    client = APIClient()
    mod.run(client)


if __name__ == "__main__":
    main()
