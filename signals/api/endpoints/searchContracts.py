import sys
import json
import argparse
import requests

from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL



def run(client):
    """
    Commande CLI :
        python main.py search <searchText> [--live true|false]
    """

    parser = argparse.ArgumentParser(description="Recherche de contrats par nom")
    parser.add_argument("searchText", type=str, help="Nom du contrat à rechercher (ex: NQ)")
    parser.add_argument("--live", type=str, choices=["true", "false"], default="false", help="Recherche en live mode ?")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])

    live_mode = args.live.lower() == "true"
    search_text = args.searchText

    payload = {
        "searchText": search_text,
        "live": live_mode
    }

    endpoint_name = "searchContracts"
    url = f"{BASE_URL}{CONFIG['api']['endpoints'][endpoint_name]}"

    headers = {
        "Authorization": f"Bearer {client.login()}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    enable_logging = CONFIG.get("logging", {}).get("enable_api_logging", False) or args.debug
    dry_run = CONFIG.get("logging", {}).get("dry_run_mode", False)

    if enable_logging:
        print(f"🔍 [API Call] POST {url}")
        print(f"   Headers: {headers}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")

    if dry_run:
        print("🧪 [DRY RUN] Simulation de recherche de contrats.")
        return

    try:
        response = requests.post(url, headers=headers, json=payload)

        if enable_logging:
            print(f"   Status Code: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        if data.get("success") and data.get("errorCode") == 0:
            contracts = data.get("contracts", [])
            print(f"✅ {len(contracts)} contrat(s) trouvé(s) :")
            for contract in contracts:
                print(f"- {contract['id']} | {contract['name']} | {contract['description']}")
        else:
            print(f"❌ Erreur API : {data.get('errorMessage')}")

    except Exception as e:
        print(f"❌ Exception pendant la requête : {e}")
