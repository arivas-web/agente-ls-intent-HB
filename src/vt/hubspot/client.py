"""Cliente HubSpot de SOLO LECTURA (la escritura se añadirá aparte, en dry-run por defecto)."""
import os
import time
import requests

BASE = "https://api.hubapi.com"


class HubSpotClient:
    def __init__(self, token=None):
        self.token = token or os.environ["HUBSPOT_TOKEN"]
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {self.token}"})

    def request(self, method, path, **kw):
        """Devuelve (status, json|None). Reintenta en 429/5xx."""
        for attempt in range(5):
            r = self.s.request(method, BASE + path, timeout=30, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            try:
                body = r.json()
            except ValueError:
                body = None
            return r.status_code, body
        return r.status_code, None

    def get(self, path, **params):
        return self.request("GET", path, params=params)

    def search(self, object_type, body):
        return self.request("POST", f"/crm/v3/objects/{object_type}/search", json=body)
