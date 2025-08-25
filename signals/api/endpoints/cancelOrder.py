import sys
import json
import argparse
import requests

from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL



def run(client):
    """
    Commande CLI :
        python main.py cancel <accountId> <orderId>
        (ajoute --debug pour logs)
    """

    parser = argparse.ArgumentParser(description="Annuler un ordre existant")
    parser.add_argument("accountId", type=int, help="ID du compte")
    parser.add_argument("orderId", type=int, help="ID de l’ordre à annuler")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])
    account_id = args.accountId
    order_id = args.orderId

    payload = {
        "accountId": account_id,
        "orderId": order_id
    }

    endpoint_name = "cancelOrder"
    url = f"{BASE_URL}{CONFIG['api']['endpoints'][endpoint_name]}"

    headers = {
        "Authorization": f"Bearer {client.login()}",
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    enable_logging = CONFIG.get("logging", {}).get("enable_api_logging", False) or args.debug
    dry_run = CONFIG.get("logging", {}).get("dry_run_mode", False)

    if enable_logging:
        print(f"🛑 [API Call] POST {url}")
        print(f"
