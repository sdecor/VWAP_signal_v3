import sys
import json
import argparse
import requests

from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL



def run(client):
    """
    Commande CLI :
        python main.py modify <accountId> <orderId>
        [--size <val>] [--limitPrice <val>] [--stopPrice <val>] [--trailPrice <val>]
    """
    parser = argparse.ArgumentParser(description="Modifier un ordre ouvert")

    parser.add_argument("accountId", type=int, help="ID du compte")
    parser.add_argument("orderId", type=int, help="ID de l’ordre à modifier")
    parser.add_argument("--size", type=int, default=None)
    parser.add_argument("--limitPrice", type=float, default=None)
    parser.add_argument("--stopPrice", type=float, default=None)
    parser.add_argument("--trailPrice", type=float, default=None)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])

    payload = {
        "accountId": args.accountId,
        "orderId": args.orderId,
        "size": args.size,
        "limitPrice": args.limitPrice,
        "stopPrice": args.stopPrice,
        "trailPrice": args.trailPrice
    }

    # Supprimer les clés dont la valeur est None
    payload = {key: val for key, val in payload.items() if val is not None}

    endpoint_name = "modifyOrder"
    url = f"{BASE_URL}{CONFIG['api']['endpoints'][endpoint_name]}"

    headers = {
        "Authorization": f"Bearer {client.login()}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    enable_logging = CONFIG.get("logging", {}).get("enable_api_logging", False) or args.debug
    dry_run = CONFIG.get("logging", {}).get("dry_run_mode", False)

    if enable_logging:
        print(f"✏️ [API Call] POST {url}")
        print(f"   Headers: {headers}")
        print(f"   Payload: {json.dumps(payload, indent=2)}")

    if dry_run:
        print("🧪 [DRY RUN] Simulation de modification d’ordre.")
        return

    try:
        response = requests.post(url, headers=headers, json=payload)

        if enable_logging:
            print(f"   Status Code: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        if data.get("success") and data.get("errorCode") == 0:
            print("✅ Ordre modifié avec succès.")
        else:
            print(f"❌ Erreur API : {data.get('errorMessage')}")

    except Exception as e:
        print(f"❌ Exception pendant la modification : {e}")
