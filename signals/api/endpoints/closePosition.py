import sys
import json
import argparse
import requests

from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL



def run(client):
    """
    Commande CLI :
        python main.py close_position <accountId> <contractId>
        (ajoute --debug pour logs)
    """

    parser = argparse.ArgumentParser(description="Fermer une position ouverte")
    parser.add_argument("accountId", type=int, help="ID du compte")
    parser.add_argument("contractId", type=str, help="ID du contrat à clôturer")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])
    account_id = args.accountId
    contract_id = args.contractId

    payload = {
        "accountId": account_id,
        "contractId": contract_id
    }

    endpoint_name = "closePosition"
    url = f"{BASE_URL}{CONFIG['api_endpoints'][endpoint_name]}"

    headers = {
        "Authorization": f"Bearer {client.login()}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    enable_logging = CONFIG.get("logging", {}).get("enable_api_logging", False) or args.debug
    dry_run = CONFIG.get("logging", {}).get("dry_run_mode", False)

    if enable_logging:
        print(f"📤 [API Call] POST {url}")
        print(f"   Headers: {headers}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")

    if dry_run:
        print("🧪 [DRY RUN] Simulation de fermeture de position.")
        return

    try:
        response = requests.post(url, headers=headers, json=payload)

        if enable_logging:
            print(f"   Status Code: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        if data.get("success") and data.get("errorCode") == 0:
            print("✅ Position fermée avec succès.")
        else:
            print(f"❌ Erreur API : {data.get('errorMessage')}")

    except Exception as e:
        print(f"❌ Exception pendant la requête : {e}")
