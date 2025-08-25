import requests
from signals.api.auth import authenticate
from signals.api.config import CONFIG
from signals.utils.env_loader import BASE_URL


class APIClient:
    def __init__(self, debug=False):
        self.base_url = BASE_URL
        self.endpoints = CONFIG["api"]["endpoints"]
        self.token = None
        self.debug = debug

    def login(self):
        """
        Authentifie et retourne un token, en le réutilisant si déjà chargé.
        """
        if self.token:
            return self.token
        self.token = authenticate()
        return self.token

    def headers(self):
        """
        Retourne les headers avec le token d'autorisation.
        """
        return {
            "Authorization": f"Bearer {self.login()}",
            "accept": "application/json",
            "Content-Type": "application/json"
        }

    def endpoint(self, name):
        """
        Retourne le chemin d'un endpoint défini dans config.yaml.
        """
        if name not in self.endpoints:
            raise KeyError(f"Endpoint '{name}' non trouvé dans config.yaml")
        return self.endpoints[name]

    def url_for(self, name):
        """
        Construit l'URL complète vers un endpoint.
        """
        return self.base_url + self.endpoint(name)

    def post(self, endpoint_name, payload, strict=True):
        """
        Envoie une requête POST à un endpoint donné.
        """
        url = self.url_for(endpoint_name)
        headers = self.headers()

        if self.debug:
            print(f"📡 POST {url}")
            print(f"Payload: {payload}")

        response = requests.post(url, json=payload, headers=headers)

        if self.debug:
            print(f"Status: {response.status_code}")

        if not response.ok and strict:
            response.raise_for_status()

        return response.json()
