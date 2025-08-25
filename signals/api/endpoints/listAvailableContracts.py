import requests
import sys
import json
from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL


def run(client):
    """
    Commande CLI :
        python main.py available [--live true|false]
    """

    import argparse
    parser = argparse.ArgumentParser(description="Lister les contrats disponibles")
    parser.add_argument("--live", type=str, choices=["true", "false"], default="false", help="Mode live ou sim ?")
    args = parser.parse_args(sys.argv[2:])

    live_mode = args.live.lower() == "true"
    token = client.login()

    url = f"{BASE_URL}{CONFIG['api']['endpoints']['listAvailableContracts']}"
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "live": live_mode
    }

    enable_logging = CONFIG.get("logging", {}).get("enable_api_logging", False)
    dry_run = CONFIG.get("logging", {}).get("dry_run_mode", False)

    if enable_logging:
        print(f"📄 [API Call] POST {url}")
        print(f"   Headers: {headers}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")

    if dry_run:
        print("🧪 [DRY RUN] Simulation de récupération des contrats disponibles.")
        return

    try:
        response = requests.post(url, headers=headers, json=payload)
        if enable_logging:
            print(f"   Status Code: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        if data.get("success") and data.get("errorCode") == 0:
            contracts = data.get("contracts", [])
            print(f"✅ {len(contracts)} contrat(s) disponible(s) :")
            for contract in contracts:
                print(f"- {contract['id']} | {contract['name']} | {contract['description']}")
        else:
            print(f"❌ Erreur API : {data.get('errorMessage')}")

    except Exception as e:
        print(f"❌ Exception pendant la requête : {e}")
