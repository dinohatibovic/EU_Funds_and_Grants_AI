from rag.pipeline import RAGPipeline

class RAGClient:
    def __init__(self):
        self.pipeline = RAGPipeline()

    def get_context(self, query: str) -> str:
        result = self.pipeline.run(query)
        return result.get("context", None)

