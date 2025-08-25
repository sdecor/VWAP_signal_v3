import sys
import json
import argparse
import uuid


def run(client):
    """
    Commande CLI :
        python main.py brackets <accountId> <contractId> <side> <size>
        --entryType <type> --entryPrice <price>
        --stopPrice <price> --limitPrice <price>
        [--debug]

    Type: 1=Limit, 2=Market, 4=Stop, 5=TrailingStop, 6=JoinBid, 7=JoinAsk
    Side: 0=Buy, 1=Sell
    """

    parser = argparse.ArgumentParser(description="Placer un ordre bracket (entrée + TP + SL)")
    parser.add_argument("accountId", type=int)
    parser.add_argument("contractId", type=str)
    parser.add_argument("side", type=int, choices=[0, 1])
    parser.add_argument("size", type=int)
    parser.add_argument("--entryType", type=int, required=True)
    parser.add_argument("--entryPrice", type=float, required=False)
    parser.add_argument("--stopPrice", type=float, required=True)
    parser.add_argument("--limitPrice", type=float, required=True)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args(sys.argv[2:])
    debug = args.debug or client.debug

    common_payload = {
        "accountId": args.accountId,
        "contractId": args.contractId,
        "side": args.side,
        "size": args.size,
    }

    try:
        # Créer un tag unique pour l'ensemble
        group_tag = str(uuid.uuid4())

        # 1. Entrée
        entry_payload = {
            **common_payload,
            "type": args.entryType,
            "limitPrice": args.entryPrice if args.entryType == 1 else None,
            "customTag": f"{group_tag}-entry"
        }
        entry_payload = {k: v for k, v in entry_payload.items() if v is not None}
        entry_data = client.post("placeOrder", entry_payload)
        entry_id = entry_data.get("orderId")

        if not entry_id:
            raise Exception("Échec de création de l'ordre d’entrée.")

        print(f"✅ Entrée créée (orderId={entry_id})")

        # 2. Stop Loss
        stop_payload = {
            **common_payload,
            "type": 4,  # Stop
            "stopPrice": args.stopPrice,
            "customTag": f"{group_tag}-sl",
            "linkedOrderId": entry_id
        }
        stop_data = client.post("placeOrder", stop_payload)

        if stop_data.get("orderId"):
            print(f"✅ Stop loss créé (orderId={stop_data['orderId']})")
        else:
            print("❌ Erreur lors de la création du stop loss.")

        # 3. Take Profit
        tp_payload = {
            **common_payload,
            "type": 1,  # Limit
            "limitPrice": args.limitPrice,
            "customTag": f"{group_tag}-tp",
            "linkedOrderId": entry_id
        }
        tp_data = client.post("placeOrder", tp_payload)

        if tp_data.get("orderId"):
            print(f"✅ Take profit créé (orderId={tp_data['orderId']})")
        else:
            print("❌ Erreur lors de la création du take profit.")

        if debug:
            print("\n📦 Bracket complet :")
            print(json.dumps({
                "entry": entry_payload,
                "stop": stop_payload,
                "take_profit": tp_payload
            }, indent=2))

    except Exception as e:
        print(f"❌ Exception lors du placement du bracket : {e}")
