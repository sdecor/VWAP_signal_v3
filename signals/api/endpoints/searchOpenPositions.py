import sys
import json
import argparse
import requests

from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL



def run(client):
    """
    Commande CLI :
        python main.py searchOpenPositions <accountId>
        (ajoute --debug pour logs supplémentaires)
    """

    parser = argparse.ArgumentParser(description="Rechercher les positions ouvertes")
    parser.add_argument("accountId", type=int, help="Identifiant du compte")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])
    account_id = args.accountId

    payload = {"accountId": account_id}
    endpoint_name = "searchOpenPositions"
    url = f"{BASE_URL}{CONFIG['api']['endpoints'][endpoint_name]}"

    headers = {
        "Authorization": f"Bearer {client.login()}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    enable_logging = CONFIG.get("logging", {}).get("enable_api_logging", False) or args.debug
    dry_run = CONFIG.get("logging", {}).get("dry_run_mode", False)

    if enable_logging:
        print(f"📡 [API Call] POST {url}")
        print(f"   Headers: {headers}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")

    if dry_run:
        print("🧪 [DRY RUN] Simulation de recherche de positions ouvertes.")
        return

    try:
        response = requests.post(url, headers=headers, json=payload)

        if enable_logging:
            print(f"   Status Code: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        if data.get("success") and data.get("errorCode") == 0:
            positions = data.get("positions", [])
            print(f"✅ {len(positions)} position(s) ouverte(s) trouvée(s).")
            for pos in positions:
                print(json.dumps(pos, indent=2))
        else:
            print(f"❌ Erreur API : {data.get('errorMessage')}")

    except Exception as e:
        print(f"❌ Exception pendant la requête : {e}")
