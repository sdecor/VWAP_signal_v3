import sys
import json
import uuid
import argparse


def run(client):
    """
    Commande CLI :
        python main.py placeOrder <accountId> <contractId> <type> <side> <size>
        [--limitPrice <val>] [--stopPrice <val>] [--trailPrice <val>] 
        [--customTag <tag>] [--linkedOrderId <id>] [--debug]

    type: 1=Limit, 2=Market, 4=Stop, 5=TrailingStop, 6=JoinBid, 7=JoinAsk
    side: 0=Buy, 1=Sell
    """
    parser = argparse.ArgumentParser(description="Placer un ordre via l’API TopstepX")
    parser.add_argument("accountId", type=int)
    parser.add_argument("contractId", type=str)
    parser.add_argument("type", type=int, choices=[1, 2, 4, 5, 6, 7])
    parser.add_argument("side", type=int, choices=[0, 1])
    parser.add_argument("size", type=int)
    parser.add_argument("--limitPrice", type=float, default=None)
    parser.add_argument("--stopPrice", type=float, default=None)
    parser.add_argument("--trailPrice", type=float, default=None)
    parser.add_argument("--customTag", type=str, default=str(uuid.uuid4()))
    parser.add_argument("--linkedOrderId", type=int, default=None)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])

    payload = {
        "accountId": args.accountId,
        "contractId": args.contractId,
        "type": args.type,
        "side": args.side,
        "size": args.size,
        "limitPrice": args.limitPrice,
        "stopPrice": args.stopPrice,
        "trailPrice": args.trailPrice,
        "customTag": args.customTag,
        "linkedOrderId": args.linkedOrderId,
    }

    # Supprimer les clés avec des valeurs nulles
    payload = {k: v for k, v in payload.items() if v is not None}

    endpoint_name = "placeOrder"

    try:
        endpoint_url = client.url_for(endpoint_name)

        if client.debug or args.debug:
            print(f"🔎 Endpoint '{endpoint_name}' → '{endpoint_url}'")
            print(f"🔗 URL: {endpoint_url}")
            print(f"📦 Payload: {json.dumps(payload, indent=2)}")

        data = client.post(endpoint_name, payload)

        if isinstance(data, dict) and data.get("success") and data.get("errorCode") == 0:
            order_id = data.get("orderId")
            if order_id:
                print(f"✅ Ordre placé avec succès. orderId={order_id}")
            else:
                print("✅ Ordre placé avec succès.")
        else:
            print("❌ Erreur de l’API :")
            print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"❌ Exception pendant le placement d’ordre : {e}")
