import os
from pymilvus import DataType, FieldSchema, MilvusClient
import requests
from langchain_community.document_loaders import BiliBiliLoader
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers import SelfQueryRetriever
from langchain_community.vectorstores import Chroma
from langchain.chat_models import init_chat_model
import logging
from dotenv import load_dotenv  
from rich import traceback
from embedding import EmbeddingService

load_dotenv()
logging.basicConfig(level=logging.INFO)
traceback.install()


class SimpleKnowledgeBase:
    """知识库"""
    
    def __init__(self, milvus_uri: str = "http://localhost:19530"):
        self.milvus_uri = milvus_uri
        self.client = MilvusClient(uri=milvus_uri)
        self.embedding_function = EmbeddingService()
        self.collection_name = "text2sql_kb"
        self._setup_collection()
    def _setup_collection(self):       
        """设置集合"""
        # 定义字段
        fields = [
            FieldSchema(name="pk", dtype=DataType.VARCHAR, is_primary=True, auto_id=True, max_length=100),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=32),  # ddl, qsql, description
            FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_function.dim["dense"])
        ]
