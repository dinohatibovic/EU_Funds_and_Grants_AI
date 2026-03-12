from rag.pipeline import RAGPipeline


class MainAgent:
    """High-level agent orchestrating multi-step reasoning."""

    def __init__(self):
        self.rag = RAGPipeline()

    def answer(self, query: str) -> str:
        results = self.rag.search(query)
        if not results:
            return "Nisu pronađeni relevantni grantovi za ovaj upit."
        context = "\n".join([f"{r['rank']}. {r['title']} ({r['category']}): {r['text'][:200]}" for r in results])
        return f"Pronađeni grantovi:\n\n{context}"
