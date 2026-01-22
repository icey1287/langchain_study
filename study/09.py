import os
import requests
from langchain_community.document_loaders import BiliBiliLoader
from langchain_classic.chains.query_constructor.schema import AttributeInfo
from langchain_classic.retrievers import SelfQueryRetriever
from langchain_community.vectorstores import Chroma
from langchain.chat_models import init_chat_model
import logging
from dotenv import load_dotenv  
from rich import traceback
# from embedding import EmbeddingService

load_dotenv()
logging.basicConfig(level=logging.INFO)
traceback.install()


class SimpleEmbeddings:
    def __init__(self):
        self.base_url = os.getenv("BASE_URL")
        self.embedder = os.getenv("EMBEDDER")
        self.api_key = os.getenv("ARK_API_KEY")

    def embed_documents(self, texts):
        clean = [str(t) for t in texts]
        payload = {"model": self.embedder, "input": clean, "encoding_format": "float"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(f"{self.base_url}/embeddings", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "data" not in data:
            raise RuntimeError(f"embedder 响应缺少 data 字段: {data}")
        return [item["embedding"] for item in data["data"]]

    def embed_query(self, text):
        return self.embed_documents([text])[0]



# 1. 初始化视频数据
video_urls = [
    "https://www.bilibili.com/video/BV1Bo4y1A7FU", 
    "https://www.bilibili.com/video/BV1ug4y157xA",
    "https://www.bilibili.com/video/BV1yh411V7ge",
]

bili = []
texts = []
metas = []
try:
    loader = BiliBiliLoader(video_urls=video_urls)
    docs = loader.load()
    
    for doc in docs:
        original = doc.metadata
        
        # 提取基本元数据字段
        metadata = {
            'title': original.get('title', '未知标题'),
            'author': original.get('owner', {}).get('name', '未知作者'),
            'source': original.get('bvid', '未知ID'),
            'view_count': original.get('stat', {}).get('view', 0),
            'length': original.get('duration', 0),
        }
        
        doc.metadata = metadata
        doc.page_content = ""  # 不使用正文
        bili.append(doc)

        text = f"标题:{metadata['title']} 作者:{metadata['author']} 时长:{metadata['length']}秒 观看:{metadata['view_count']}"
        texts.append(text)
        metas.append(metadata)
        
except Exception as e:
    print(f"加载BiliBili视频失败: {str(e)}")

if not bili:
    print("没有成功加载任何视频，程序退出")
    exit()

# 2. 创建向量存储
embed_model = SimpleEmbeddings()
vectorstore = Chroma.from_texts(texts=texts, embedding=embed_model, metadatas=metas)

# 3. 配置元数据字段信息
metadata_field_info = [
    AttributeInfo(
        name="title",
        description="视频标题（字符串）",
        type="string", 
    ),
    AttributeInfo(
        name="author",
        description="视频作者（字符串）",
        type="string",
    ),
    AttributeInfo(
        name="view_count",
        description="视频观看次数（整数）",
        type="integer",
    ),
    AttributeInfo(
        name="length",
        description="视频长度，以秒为单位的整数",
        type="integer"
    )
]

print(bili)
# 4. 创建自查询检索器
llm = init_chat_model(
    model=os.getenv("MODEL"),
    model_provider="openai",
    api_key=os.getenv("ARK_API_KEY"),
    base_url=os.getenv("BASE_URL"),
)

retriever = SelfQueryRetriever.from_llm(
    llm=llm,
    vectorstore=vectorstore,
    document_contents="记录视频标题、作者、观看次数等信息的视频元数据",
    metadata_field_info=metadata_field_info,
    enable_limit=True,
    verbose=True
)

# 5. 执行查询示例
queries = [
    "时间最短的视频",
    "时长大于600秒的视频"
]

for query in queries:
    print(f"\n--- 查询: '{query}' ---")
    results = retriever.invoke(query)
    if results:
        for doc in results:
            title = doc.metadata.get('title', '未知标题')
            author = doc.metadata.get('author', '未知作者')
            view_count = doc.metadata.get('view_count', '未知')
            length = doc.metadata.get('length', '未知')
            print(f"标题: {title}")
            print(f"作者: {author}")
            print(f"观看次数: {view_count}")
            print(f"时长: {length}秒")
            print("="*50)
    else:
        print("未找到匹配的视频")

