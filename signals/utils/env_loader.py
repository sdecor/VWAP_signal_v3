# utils/env_loader.py

import os
from dotenv import load_dotenv

def load_env():
    """Charge les variables d'environnement depuis un fichier .env"""
    load_dotenv()

# Variables globales (facultatives — si tu veux toujours les exposer)
API_KEY = os.getenv("TOPSTEPX_API_KEY")
BASE_URL = os.getenv("TOPSTEPX_BASE_URL")
USERNAME = os.getenv("TOPSTEPX_USERNAME")
ACCOUNT_ID = os.getenv("TOPSTEPX_ACCOUNT_ID")
