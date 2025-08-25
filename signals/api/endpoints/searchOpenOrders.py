import sys
import json
import argparse

from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL



# Aide pour certains codes d'erreur
ERROR_HINTS = {
    1: "Compte invalide, pas d'accès ou aucun ordre ouvert. Vérifie accountId/permissions.",
    2: "Paramètres requis manquants ou invalides.",
}


def run(client):
    """
    Commande CLI :
        python main.py searchOpenOrders <accountId>
        python main.py searchOpenOrders --accountId 212
        python main.py searchOpenOrders --raw   # dump complet JSON
        (ajoute --debug pour logs supplémentaires)
    """

    parser = argparse.ArgumentParser(description="Lister les ordres ouverts")
    parser.add_argument("accountId", nargs="?", type=int, default=None, help="ID du compte")
    parser.add_argument("--accountId", dest="accountIdFlag", type=int, default=None, help="ID du compte (optionnel)")
    parser.add_argument("--raw", action="store_true", help="Afficher la réponse brute JSON")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])

    # Priorité : --accountId > positionnel > .env
    account_id = args.accountIdFlag or args.accountId or (int(ENV_ACCOUNT_ID) if ENV_ACCOUNT_ID else None)

    if account_id is None:
        print("❌ accountId manquant. Fournis-le en argument ou via .env TOPSTEPX_ACCOUNT_ID.")
        return

    payload = {"accountId": account_id}
    endpoint_name = "searchOpenOrders"

    try:
        url = client.url_for(endpoint_name)

        if args.debug or client.debug:
            print(f"🔎 Endpoint '{endpoint_name}' → '{url}'")
            print(f"📦 Payload: {json.dumps(payload, indent=2)}")

    except KeyError as ke:
        print(f"❌ Endpoint manquant dans la config : {ke}")
        return

    try:
        # strict=False : permet d'afficher les erreurs API sans lever une exception
        data = client.post(endpoint_name, payload, strict=False)

        if args.raw or not isinstance(data, dict):
            print(json.dumps(data, indent=2))
            return

        if data.get("success") and data.get("errorCode") == 0:
            orders = data.get("orders", [])
            if orders:
                print(f"✅ {len(orders)} ordre(s) ouvert(s) pour le compte {account_id} :")
                for order in orders:
                    print(json.dumps(order, indent=2))
            else:
                print(f"ℹ️ Aucun ordre ouvert pour le compte {account_id}.")
        else:
            code = data.get("errorCode")
            msg = data.get("errorMessage") or ERROR_HINTS.get(code, "Erreur inconnue.")
            print(f"❌ API errorCode={code} → {msg}")
            if args.debug:
                print("—— Réponse complète ——")
                print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"❌ Erreur lors de la récupération des ordres ouverts : {e}")
