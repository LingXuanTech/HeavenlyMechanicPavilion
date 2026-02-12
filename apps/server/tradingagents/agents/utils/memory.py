import chromadb
from chromadb.config import Settings
from openai import OpenAI
import structlog

logger = structlog.get_logger(__name__)


def _get_openai_client_config():
    """从 ai_config_service 获取 OpenAI 兼容的客户端配置

    Returns:
        {"base_url": "...", "api_key": "..."} 或 None
    """
    try:
        from services.ai_config_service import ai_config_service
        return ai_config_service.get_openai_client_config()
    except Exception:
        return None


class FinancialSituationMemory:
    def __init__(self, name, config):
        self._use_openai_embedding = False
        self.client = None
        self.embedding = None

        # 尝试从 ai_config_service 获取 OpenAI 兼容客户端配置
        client_config = _get_openai_client_config()

        if client_config:
            base_url = client_config["base_url"]
            self.client = OpenAI(base_url=base_url, api_key=client_config["api_key"])
            # 本地 Ollama 使用 nomic-embed-text，其他使用 OpenAI 标准模型
            if "localhost:11434" in base_url:
                self.embedding = "nomic-embed-text"
            else:
                self.embedding = "text-embedding-3-small"
            self._use_openai_embedding = True
        elif config.get("backend_url"):
            # CLI 模式降级：使用 config 中的 backend_url
            try:
                self.client = OpenAI(base_url=config["backend_url"])
                if config["backend_url"] == "http://localhost:11434/v1":
                    self.embedding = "nomic-embed-text"
                else:
                    self.embedding = "text-embedding-3-small"
                self._use_openai_embedding = True
            except Exception as e:
                logger.warning("Failed to create OpenAI embedding client from config", error=str(e))

        if not self._use_openai_embedding:
            logger.info("No OpenAI-compatible provider available, using chromadb default embedding", name=name)

        self.chroma_client = chromadb.Client(Settings(allow_reset=True))
        # 不使用 OpenAI embedding 时，chromadb 使用内置的 default embedding function
        self.situation_collection = self.chroma_client.create_collection(name=name)

    def get_embedding(self, text):
        """Get embedding for a text

        使用 OpenAI 兼容 API 或返回 None（由 chromadb 使用内置 embedding）
        """
        if self._use_openai_embedding and self.client:
            response = self.client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding
        return None

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            emb = self.get_embedding(situation)
            if emb is not None:
                embeddings.append(emb)

        add_kwargs = {
            "documents": situations,
            "metadatas": [{"recommendation": rec} for rec in advice],
            "ids": ids,
        }
        # 只在有 OpenAI embedding 时传入，否则让 chromadb 使用内置 embedding
        if embeddings:
            add_kwargs["embeddings"] = embeddings

        self.situation_collection.add(**add_kwargs)

    def get_memories(self, current_situation, n_matches=1):
        """Find matching recommendations using embeddings"""
        query_embedding = self.get_embedding(current_situation)

        query_kwargs = {
            "n_results": n_matches,
            "include": ["metadatas", "documents", "distances"],
        }
        # OpenAI embedding 可用时使用自定义 embedding，否则让 chromadb 用文本查询
        if query_embedding is not None:
            query_kwargs["query_embeddings"] = [query_embedding]
        else:
            query_kwargs["query_texts"] = [current_situation]

        results = self.situation_collection.query(**query_kwargs)

        matched_results = []
        for i in range(len(results["documents"][0])):
            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": results["metadatas"][0][i]["recommendation"],
                    "similarity_score": 1 - results["distances"][0][i],
                }
            )

        return matched_results


if __name__ == "__main__":
    # Example usage
    matcher = FinancialSituationMemory()

    # Example data
    example_data = [
        (
            "High inflation rate with rising interest rates and declining consumer spending",
            "Consider defensive sectors like consumer staples and utilities. Review fixed-income portfolio duration.",
        ),
        (
            "Tech sector showing high volatility with increasing institutional selling pressure",
            "Reduce exposure to high-growth tech stocks. Look for value opportunities in established tech companies with strong cash flows.",
        ),
        (
            "Strong dollar affecting emerging markets with increasing forex volatility",
            "Hedge currency exposure in international positions. Consider reducing allocation to emerging market debt.",
        ),
        (
            "Market showing signs of sector rotation with rising yields",
            "Rebalance portfolio to maintain target allocations. Consider increasing exposure to sectors benefiting from higher rates.",
        ),
    ]

    # Add the example situations and recommendations
    matcher.add_situations(example_data)

    # Example query
    current_situation = """
    Market showing increased volatility in tech sector, with institutional investors 
    reducing positions and rising interest rates affecting growth stock valuations
    """

    try:
        recommendations = matcher.get_memories(current_situation, n_matches=2)

        for i, rec in enumerate(recommendations, 1):
            print(f"\nMatch {i}:")
            print(f"Similarity Score: {rec['similarity_score']:.2f}")
            print(f"Matched Situation: {rec['matched_situation']}")
            print(f"Recommendation: {rec['recommendation']}")

    except Exception as e:
        print(f"Error during recommendation: {str(e)}")
