import sys
from api.config import CONFIG, debug_dump_config
from api.client import TopstepClient

# Import des handlers
from api.endpoints.placeOrder import run as place_order
from api.endpoints.modifyOrder import run as modify_order
from api.endpoints.cancelOrder import run as cancel_order
from api.endpoints.searchOpenOrders import run as search_open_orders
from api.endpoints.searchOpenPositions import run as search_open_positions
from api.endpoints.closePosition import run as close_position
from api.endpoints.searchContracts import run as search_contracts
from api.endpoints.searchContractById import run as search_contract_by_id
from api.endpoints.listAvailableContracts import run as list_available_contracts
# Ajuste si tu renommes en singular:
from api.endpoints.bracketOrders import run as bracket_orders

COMMANDS = {
    "placeOrder": place_order,
    "modifyOrder": modify_order,
    "cancelOrder": cancel_order,
    "searchOpenOrders": search_open_orders,
    "searchOpenPositions": search_open_positions,
    "closePosition": close_position,
    "searchContracts": search_contracts,
    "searchContractById": search_contract_by_id,
    "listAvailableContracts": list_available_contracts,
    "bracketOrders": bracket_orders,
}

def _extract_debug_flag(argv: list) -> tuple[bool, list]:
    """
    Extrait un flag global --debug (où qu'il soit dans la ligne de commande).
    Retourne (debug_enabled, argv_sans_debug)
    """
    cleaned = []
    debug = False
    for a in argv:
        if a == "--debug":
            debug = True
        else:
            cleaned.append(a)
    return debug, cleaned

def dispatch():
    """
    Dispatch général :
    - supporte le flag global --debug
    - dump d'infos utiles en debug (env, endpoints, cmd, argv)
    """
    if len(sys.argv) < 2:
        print("❌ Aucune commande spécifiée. Exemple : python main.py placeOrder")
        print("📌 Commandes disponibles :", ", ".join(COMMANDS.keys()))
        return

    debug, argv = _extract_debug_flag(sys.argv)
    if debug:
        print("🪵 DEBUG MODE ACTIVÉ")
        print("argv original :", sys.argv)
        print("argv nettoyé  :", argv)
        print("—— dump config ——")
        print(debug_dump_config())

    # argv[0] = script, argv[1] = commande
    if len(argv) < 2:
        print("❌ Aucune commande spécifiée après nettoyage des flags.")
        return

    command = argv[1]
    if command not in COMMANDS:
        print(f"❌ Commande inconnue : '{command}'")
        print("📌 Commandes disponibles :", ", ".join(COMMANDS.keys()))
        return

    # instancie le client ICI pour passer le debug
    client = TopstepClient(config=CONFIG, debug=debug)

    # Remplace sys.argv par argv nettoyé pour les parsers des handlers
    old_argv = sys.argv
    sys.argv = argv
    try:
        if debug:
            print(f"➡️  Commande résolue: {command}")
        COMMANDS[command](client)
    except KeyError as ke:
        print(f"❌ KeyError: {ke}")
        if debug:
            print("Indices: vérifie config.yaml (api -> endpoints -> NOM_ENDPOINT)")
    except Exception as e:
        print(f"❌ Erreur dans la commande '{command}': {e}")
        if debug:
            import traceback
            traceback.print_exc()
    finally:
        sys.argv = old_argv
