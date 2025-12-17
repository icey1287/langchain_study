"""文本向量化服务 - 只负责生成 Embedding"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()


class EmbeddingService:
    """文本向量化服务"""

    def __init__(self):
        self.base_url = os.getenv("BASE_URL")
        self.embedder = os.getenv("EMBEDDER")
        self.api_key = os.getenv("ARK_API_KEY")

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        调用嵌入 API 生成向量
        :param texts: 待转换的文本列表（支持批量）
        :return: 向量列表
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.embedder,
            "input": texts,
            "encoding_format": "float"
        }

        try:
            response = requests.post(f"{self.base_url}/embeddings", headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return [item["embedding"] for item in result["data"]]
        except Exception as e:
            raise Exception(f"嵌入 API 调用失败: {str(e)}")