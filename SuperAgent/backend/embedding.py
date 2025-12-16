import os
import requests
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from pymilvus import MilvusClient, DataType

load_dotenv()
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "embeddings_collection")
BASE_URL=os.getenv("BASE_URL")
EMBEDDER=os.getenv("EMBEDDER")
ARK_API_KEY=os.getenv("ARK_API_KEY")

milvus_client = MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}")

# PDF 文件夹路径
package_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
data_dir = os.path.join(package_root, "data")
PDF_FOLDER = data_dir

# 文本分段配置（LangChain 智能分段）
TEXT_SPLITTER_CONFIG = {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "separators": ["\n\n", "\n", "。", "！", "？", "，", "、", " ", ""]  # 适配中文分段
}

def get_embedding(texts: list[str]) -> list[list[float]]:
    """
    调用豆包嵌入 API 生成向量
    :param texts: 待转换的文本列表（支持批量，提升效率）
    :return: 向量列表（每个文本对应一个向量）
    """
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": EMBEDDER,
        "input": texts,  # 批量传入文本，减少 API 调用次数
        "encoding_format": "float"  # 向量格式：float（默认）或 base64
    }
    
    try:
        response = requests.post(BASE_URL + "/embeddings", headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        embeddings = [item["embedding"] for item in result["data"]]
        return embeddings
    except Exception as e:
        raise Exception(f"嵌入 API 调用失败: {str(e)}")

# -------------------------- 3. LangChain 处理文档（PDF + Word） --------------------------
def load_documents(doc_folder: str) -> list[dict]:
    """用 LangChain 加载 PDF 和 Word 文档并智能分段"""
    all_documents = []
    # 初始化中文文本分段器
    text_splitter = RecursiveCharacterTextSplitter(**TEXT_SPLITTER_CONFIG)
    
    # 遍历文档文件夹
    for filename in os.listdir(doc_folder):
        file_lower = filename.lower()
        file_path = os.path.join(doc_folder, filename)
        
        # 判断文件类型
        if file_lower.endswith(".pdf"):
            doc_type = "PDF"
            loader = PyPDFLoader(file_path)
        elif file_lower.endswith((".docx", ".doc")):
            doc_type = "Word"
            loader = Docx2txtLoader(file_path)
        else:
            continue
        
        # 加载并分段文档
        try:
            # 加载原始文档
            raw_docs = loader.load()
            # 智能分段（按中文语义拆分）
            split_docs = text_splitter.split_documents(raw_docs)
            
            # 整理文档元数据
            for idx, doc in enumerate(split_docs):
                all_documents.append({
                    "text": doc.page_content.strip(),
                    "filename": filename,
                    "file_path": file_path,
                    "file_type": doc_type,
                    "page_number": doc.metadata.get("page", 0),
                    "chunk_idx": idx
                })
        except Exception:
            continue
    
    return all_documents

# -------------------------- 4. Milvus 初始化与写入（复用+适配） --------------------------
def init_milvus_collection():
    if not milvus_client.has_collection(MILVUS_COLLECTION):
        schema = milvus_client.create_schema(auto_id=True, enable_dynamic_field=True)
        # 主键字段（自动生成）
        schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
        # 向量字段（2560 维，doubao-embedding-text-240715 模型）
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=2560)
        # 文本字段
        schema.add_field("text", DataType.VARCHAR, max_length=2000)
        # 文档元数据字段
        schema.add_field("filename", DataType.VARCHAR, max_length=255)
        schema.add_field("file_type", DataType.VARCHAR, max_length=50)
        schema.add_field("page_number", DataType.INT64)
        
        # 创建索引
        index_params = milvus_client.prepare_index_params()
        index_params.add_index("embedding", index_type="IVF_FLAT", metric_type="IP")
        
        # 使用命名参数调用
        milvus_client.create_collection(
            collection_name=MILVUS_COLLECTION,
            schema=schema,
            index_params=index_params
        )

def write_docs_to_milvus(docs: list[dict], batch_size=50):
    """批量写入 Milvus"""
    if not docs:
        return
    
    total = len(docs)
    for i in range(0, total, batch_size):
        batch = docs[i:i+batch_size]
        # 提取批量文本
        texts = [doc["text"] for doc in batch]
        # 生成向量
        embeddings = get_embedding(texts)
        # 构造插入数据
        insert_data = []
        for doc, emb in zip(batch, embeddings):
            insert_data.append({
                "embedding": emb,
                "text": doc["text"],
                "filename": doc["filename"],
                "file_type": doc["file_type"],
                "file_path": doc["file_path"],
                "page_number": doc["page_number"],
                "chunk_idx": doc["chunk_idx"]
            })
        # 写入 Milvus
        milvus_client.insert(MILVUS_COLLECTION, insert_data)

if __name__ == "__main__":
    init_milvus_collection()
    docs = load_documents(PDF_FOLDER)
    if docs:
        write_docs_to_milvus(docs)