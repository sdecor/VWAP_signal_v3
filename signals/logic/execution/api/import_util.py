# signals/logic/execution/api/import_util.py

def import_api_client():
    """
    Import paresseux d'APIClient pour éviter de casser en tests/dry-run.
    """
    try:
        from signals.api.client import APIClient  # type: ignore
        return APIClient
    except Exception:
        return None
