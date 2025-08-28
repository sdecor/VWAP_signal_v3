# signals/logic/execution/api_client.py
"""
Shim de compatibilité : ré-exporte l'API modularisée.
Permet de conserver les imports existants: from signals.logic.execution import api_client as api
"""

from .api import import_api_client, place_order, load_api_settings

__all__ = ["import_api_client", "place_order", "load_api_settings"]
