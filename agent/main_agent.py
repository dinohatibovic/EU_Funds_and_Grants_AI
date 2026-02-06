from rag.pipeline import RAGPipeline


class MainAgent:
    """High-level agent orchestrating multi-step reasoning."""

    def __init__(self):
        self.rag = RAGPipeline()

    def answer(self, query: str) -> str:
        result = self.rag.run(query)
        return f"Contextual answer based on retrieved grants:\n\n{result['context']}"
