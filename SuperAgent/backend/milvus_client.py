"""Milvus 客户端 - 只负责连接和集合管理"""
import os
from dotenv import load_dotenv
from pymilvus import MilvusClient, DataType

load_dotenv()


class MilvusManager:
    """Milvus 连接和集合管理"""

    def __init__(self):
        self.host = os.getenv("MILVUS_HOST", "localhost")
        self.port = os.getenv("MILVUS_PORT", "19530")
        self.collection_name = os.getenv("MILVUS_COLLECTION", "embeddings_collection")
        self.client = MilvusClient(uri=f"http://{self.host}:{self.port}")

    def init_collection(self, vector_dim: int = 2560):
        """初始化 Milvus 集合"""
        if not self.client.has_collection(self.collection_name):
            schema = self.client.create_schema(auto_id=True, enable_dynamic_field=True)
            schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
            schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=vector_dim)
            schema.add_field("text", DataType.VARCHAR, max_length=2000)
            schema.add_field("filename", DataType.VARCHAR, max_length=255)
            schema.add_field("file_type", DataType.VARCHAR, max_length=50)
            schema.add_field("page_number", DataType.INT64)

            index_params = self.client.prepare_index_params()
            index_params.add_index("embedding", index_type="IVF_FLAT", metric_type="IP")

            self.client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params
            )

    def insert(self, data: list[dict]):
        """插入数据到 Milvus"""
        return self.client.insert(self.collection_name, data)

    def query(self, filter_expr: str = "", output_fields: list[str] = None, limit: int = 10000):
        """查询数据"""
        return self.client.query(
            collection_name=self.collection_name,
            filter=filter_expr,
            output_fields=output_fields or ["filename", "file_type"],
            limit=limit
        )

    def delete(self, filter_expr: str):
        """删除数据"""
        return self.client.delete(
            collection_name=self.collection_name,
            filter=filter_expr
        )

    def has_collection(self) -> bool:
        """检查集合是否存在"""
        return self.client.has_collection(self.collection_name)
