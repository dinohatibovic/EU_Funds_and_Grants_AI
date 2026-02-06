import requests


def fetch_from_api(endpoint: str, params: dict = None) -> list[dict]:
    response = requests.get(endpoint, params=params)
    response.raise_for_status()
    return response.json()

