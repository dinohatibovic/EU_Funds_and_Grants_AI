from .genai_client import GenAIClient
from .rag_client import RAGClient

class EUFundsAgent:
    def __init__(self):
        print("🤖 Inicijalizacija agenta (stable API, bez embeddinga)...")
        self.rag = RAGClient()
        self.genai = GenAIClient()

    def answer(self, query: str) -> str:
        rag_result = self.rag.get_context(query)
        has_context = rag_result and rag_result != "Nema rezultata."

        if has_context:
            prompt = f"""
Ti si ekspert za EU fondove i grantove.
Odgovori ISKLJUČIVO na osnovu konteksta.

Pitanje:
{query}

Kontekst:
{rag_result}
"""
        else:
            prompt = f"""
Ti si ekspert za EU fondove i grantove.
Odgovori na pitanje koristeći svoje znanje, strukturirano i jasno.

Pitanje:
{query}
"""

        return self.genai.generate(prompt)
