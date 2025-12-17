"""文档向量化并写入 Milvus"""
try:
    from .embedding import EmbeddingService
    from .milvus_client import MilvusManager
except ImportError:
    from embedding import EmbeddingService
    from milvus_client import MilvusManager


class MilvusWriter:
    """文档向量化并写入 Milvus 服务"""

    def __init__(self, embedding_service: EmbeddingService = None, milvus_manager: MilvusManager = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self.milvus_manager = milvus_manager or MilvusManager()

    def write_documents(self, documents: list[dict], batch_size: int = 50):
        """
        批量写入文档到 Milvus
        :param documents: 文档列表
        :param batch_size: 批次大小
        """
        if not documents:
            return

        self.milvus_manager.init_collection()

        total = len(documents)
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            texts = [doc["text"] for doc in batch]
            embeddings = self.embedding_service.get_embeddings(texts)

            insert_data = [
                {
                    "embedding": emb,
                    "text": doc["text"],
                    "filename": doc["filename"],
                    "file_type": doc["file_type"],
                    "file_path": doc["file_path"],
                    "page_number": doc["page_number"],
                    "chunk_idx": doc["chunk_idx"]
                }
                for doc, emb in zip(batch, embeddings)
            ]

            self.milvus_manager.insert(insert_data)
