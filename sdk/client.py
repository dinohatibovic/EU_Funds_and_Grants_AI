"""
sdk/client.py — Javni SDK interfejs za FinAssistBH
Odgovornost: jedinstven ulazni punkt za vanjske pozive API-ja.

Primjer korištenja:
    from sdk.client import EUGrantsClient
    client = EUGrantsClient()
    response = client.query("Poticaji za MSP u ZDK kantonu")
    print(response)
"""

import requests
import os


class EUGrantsClient:
    """Jednostavan HTTP klijent za FinAssistBH pretragu grantova."""

    def __init__(self, base_url: str = None):
        # Dozvoli override baze URL-a (npr. za testove ili staging)
        self.base_url = (base_url or os.getenv("FINASSIST_API_URL", "https://eu-funds-and-grants-ai.onrender.com")).rstrip("/")

    def query(self, text: str, n_results: int = 5) -> str:
        """
        Pretražuje bazu grantova i vraća formatirani odgovor.

        Args:
            text: Korisnički upit na bosanskom ili engleskom
            n_results: Broj rezultata (1-20)

        Returns:
            Formatirani string sa listom grantova ili poruka o grešci
        """
        if not text or not text.strip():
            return "Upit ne može biti prazan."

        try:
            resp = requests.post(
                f"{self.base_url}/search",
                json={"query": text.strip(), "n_results": n_results},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.ConnectionError:
            return f"Greška: ne mogu se povezati na API ({self.base_url}). Provjeri da li je server pokrenut."
        except requests.exceptions.Timeout:
            return "Greška: API nije odgovorio na vrijeme (timeout 30s). Render free tier može biti u cold startu — pokušaj ponovo."
        except requests.exceptions.HTTPError as e:
            return f"Greška: API vratio HTTP {e.response.status_code}."
        except Exception as e:
            return f"Neočekivana greška: {e}"

        results = data.get("results", [])
        metadatas = data.get("metadatas", [[]])[0] if data.get("metadatas") else []

        if not results:
            return "Nisu pronađeni relevantni grantovi za ovaj upit."

        lines = [f"Pronađeno {len(results)} rezultata:\n"]
        for i, (text_doc, meta) in enumerate(zip(results, metadatas), 1):
            title = meta.get("title", f"Rezultat {i}")
            category = meta.get("category", "")
            budget = meta.get("budget", "")
            deadline = meta.get("deadline", "")
            url = meta.get("url", "")

            lines.append(f"{i}. {title}")
            if category:
                lines.append(f"   Kategorija: {category}")
            if budget:
                lines.append(f"   Budžet: {budget}")
            if deadline:
                lines.append(f"   Rok: {deadline}")
            if url:
                lines.append(f"   URL: {url}")
            lines.append("")

        return "\n".join(lines)
