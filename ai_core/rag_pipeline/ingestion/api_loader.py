import requests


def fetch_from_api(endpoint: str, params: dict = None, timeout: int = 30) -> list[dict]:
    response = requests.get(endpoint, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()
