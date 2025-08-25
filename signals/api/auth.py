import requests
from signals.utils.env_loader import USERNAME, API_KEY, BASE_URL
from signals.api.config import CONFIG


def authenticate():
    """
    Authentifie avec API key + username pour obtenir un token JWT.
    """

    if not USERNAME or not API_KEY:
        raise ValueError("TOPSTEPX_USERNAME ou TOPSTEPX_API_KEY non défini dans .env")

    login_url = BASE_URL + CONFIG["api"]["endpoints"]["loginKey"]

    headers = {
        "accept": "text/plain",
        "Content-Type": "application/json"
    }

    payload = {
        "userName": USERNAME,
        "apiKey": API_KEY
    }

    response = requests.post(login_url, json=payload, headers=headers)

    if response.status_code != 200:
        raise ConnectionError(f"Erreur HTTP: {response.status_code} – {response.text}")

    data = response.json()

    if not data.get("success") or not data.get("token"):
        raise Exception(f"Échec de l'authentification : {data.get('errorMessage')}")

    return data["token"]
