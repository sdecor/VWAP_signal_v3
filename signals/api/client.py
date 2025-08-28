# signals/api/client.py

import requests
import time
import logging
from requests.exceptions import RequestException

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def safe_post(url, json_data, headers=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"[API] POST {url} | tentative {attempt}")
            response = requests.post(url, json=json_data, headers=headers)
            response.raise_for_status()
            return response
        except RequestException as e:
            logging.warning(f"[API] Erreur lors du POST: {e} | tentative {attempt}")
            time.sleep(RETRY_DELAY)
    logging.error(f"[API] Échec POST après {MAX_RETRIES} tentatives: {url}")
    raise Exception("Échec API : max tentatives atteintes.")
