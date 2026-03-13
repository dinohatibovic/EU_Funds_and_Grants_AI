from rag.pipeline import RAGPipeline

class RAGClient:
    def __init__(self):
        self.pipeline = RAGPipeline()

    def get_context(self, query: str) -> str:
        results = self.pipeline.search(query)
        if not results:
            return "Nema rezultata."
        return "\n".join(
            f"{r['rank']}. {r['title']} ({r['category']}): {r['text'][:300]}"
            for r in results
        )

