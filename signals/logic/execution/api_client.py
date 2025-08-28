# signals/logic/execution/api_client.py

from typing import Optional, Dict, Any


def import_api_client():
    """
    Import paresseux d'APIClient pour éviter les erreurs d'import en dry-run/tests.
    """
    try:
        from signals.api.client import APIClient  # type: ignore
        return APIClient
    except Exception:
        return None


def place_order(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Appelle l’API de placement d’ordre via APIClient().post('placeOrder', ...).
    Renvoie la réponse (dict). Si indisponible, renvoie une erreur structurée.
    """
    APIClient = import_api_client()
    if APIClient is None:
        return {"status": "error", "error": "APIClient indisponible (import échoué)"}

    client = APIClient()
    try:
        resp = client.post("placeOrder", payload=payload, debug=False)
        # Uniformise le retour en dict
        return {"status": "ok", "response": resp}
    except Exception as e:
        return {"status": "error", "error": str(e)}
