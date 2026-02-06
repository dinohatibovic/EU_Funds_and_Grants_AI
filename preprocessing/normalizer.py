import re
from datetime import datetime


class Normalizer:
    """Cleans and standardizes scraped grant data."""

    @staticmethod
    def clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def normalize_date(date_str: str) -> str:
        try:
            return str(datetime.fromisoformat(date_str).date())
        except Exception:
            return date_str

