# signals/runner/live_loop.py
"""
Shim de compatibilité : délègue vers la version modulaire.
Permet de garder les anciens imports (`signals.runner.live_loop`) intacts.
"""
from signals.runner.live.orchestrator import run_live_loop  # re-export

__all__ = ["run_live_loop"]
