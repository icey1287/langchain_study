from typing import Optional
import os
import requests
from dotenv import load_dotenv
try:
    from .milvus_client import MilvusManager
    from .embedding import EmbeddingService
    from langchain_core.tools import tool
    from langchain.chat_models import init_chat_model
except ImportError:
    from milvus_client import MilvusManager
    from embedding import EmbeddingService
    from langchain_core.tools import tool
    from langchain.chat_models import init_chat_model

load_dotenv()

AMAP_WEATHER_API = os.getenv("AMAP_WEATHER_API")
AMAP_API_KEY = os.getenv("AMAP_API_KEY")
ARK_API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")

# 全局初始化检索依赖，避免反复构造
_embedding_service = EmbeddingService()
_milvus_manager = MilvusManager()

_stepback_model = None
_LAST_RAG_CONTEXT = None


def _get_stepback_model():
    global _stepback_model
    if not ARK_API_KEY or not MODEL:
        return None
    if _stepback_model is None:
        _stepback_model = init_chat_model(
            model=MODEL,
            model_provider="openai",
            api_key=ARK_API_KEY,
            base_url=BASE_URL,
            temperature=0.2,
        )
    return _stepback_model


def _generate_step_back_question(query: str) -> str:
    model = _get_stepback_model()
    if not model:
        return ""
    prompt = (
        "请将用户的具体问题抽象成更高层次、更概括的‘退步问题’，"
        "用于探寻背后的通用原理或核心概念。只输出退步问题一句话，不要解释。\n"
        f"用户问题：{query}"
    )
    try:
        return (model.invoke(prompt).content or "").strip()
    except Exception:
        return ""


def _answer_step_back_question(step_back_question: str) -> str:
    model = _get_stepback_model()
    if not model or not step_back_question:
        return ""
    prompt = (
        "请简要回答以下退步问题，提供通用原理/背景知识，"
        "控制在120字以内。只输出答案，不要列出推理过程。\n"
        f"退步问题：{step_back_question}"
    )
    try:
        return (model.invoke(prompt).content or "").strip()
    except Exception:
        return ""


def _set_last_rag_context(context: dict):
    global _LAST_RAG_CONTEXT
    _LAST_RAG_CONTEXT = context


def get_last_rag_context(clear: bool = True) -> Optional[dict]:
    """获取最近一次 RAG 检索上下文，默认读取后清空。"""
    global _LAST_RAG_CONTEXT
    context = _LAST_RAG_CONTEXT
    if clear:
        _LAST_RAG_CONTEXT = None
    return context


def get_current_weather(location: str, extensions: Optional[str] = "base") -> str:
    """获取天气信息"""
    if not location:
        return "location参数不能为空"
    if extensions not in ("base", "all"):
        return "extensions参数错误，请输入base或all"

    if not AMAP_WEATHER_API or not AMAP_API_KEY:
        return "天气服务未配置（缺少 AMAP_WEATHER_API 或 AMAP_API_KEY）"

    params = {
        "key": AMAP_API_KEY,
        "city": location,
        "extensions": extensions,
        "output": "json",
    }

    try:
        resp = requests.get(AMAP_WEATHER_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "1":
            return f"查询失败：{data.get('info', '未知错误')}"

        if extensions == "base":
            lives = data.get("lives", [])
            if not lives:
                return f"未查询到 {location} 的天气数据"
            w = lives[0]
            return (
                f"【{w.get('city', location)} 实时天气】\n"
                f"天气状况：{w.get('weather', '未知')}\n"
                f"温度：{w.get('temperature', '未知')}℃\n"
                f"湿度：{w.get('humidity', '未知')}%\n"
                f"风向：{w.get('winddirection', '未知')}\n"
                f"风力：{w.get('windpower', '未知')}级\n"
                f"更新时间：{w.get('reporttime', '未知')}"
            )

        forecasts = data.get("forecasts", [])
        if not forecasts:
            return f"未查询到 {location} 的天气预报数据"
        f0 = forecasts[0]
        out = [f"【{f0.get('city', location)} 天气预报】", f"更新时间：{f0.get('reporttime', '未知')}", ""]
        today = (f0.get("casts") or [])[0] if f0.get("casts") else {}
        out += [
            "今日天气：",
            f"  白天：{today.get('dayweather','未知')}",
            f"  夜间：{today.get('nightweather','未知')}",
            f"  气温：{today.get('nighttemp','未知')}~{today.get('daytemp','未知')}℃",
        ]
        return "\n".join(out)

    except requests.exceptions.Timeout:
        return "错误：请求天气服务超时"
    except requests.exceptions.RequestException as e:
        return f"错误：天气服务请求失败 - {e}"
    except Exception as e:
        return f"错误：解析天气数据失败 - {e}"


@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """Search for information in the knowledge base using hybrid retrieval (dense + sparse vectors)."""
    step_back_question = _generate_step_back_question(query)
    step_back_answer = _answer_step_back_question(step_back_question)
    if step_back_question or step_back_answer:
        retrieval_query = (
            f"{query}\n\n"
            f"退步问题：{step_back_question}\n"
            f"退步问题答案：{step_back_answer}"
        )
    else:
        retrieval_query = query

    try:
        dense_embeddings = _embedding_service.get_embeddings([retrieval_query])
        dense_embedding = dense_embeddings[0]
        sparse_embedding = _embedding_service.get_sparse_embedding(retrieval_query)

        results = _milvus_manager.hybrid_retrieve(
            dense_embedding=dense_embedding,
            sparse_embedding=sparse_embedding,
            top_k=5,
        )
    except Exception:
        # 降级到仅密集向量检索
        try:
            dense_embeddings = _embedding_service.get_embeddings([retrieval_query])
            dense_embedding = dense_embeddings[0]
            results = _milvus_manager.dense_retrieve(
                dense_embedding=dense_embedding,
                top_k=5,
            )
        except Exception:
            return "Knowledge base is currently unavailable."

    if not results:
        return "No relevant documents found in the knowledge base."

    _set_last_rag_context({
        "tool_used": True,
        "query": query,
        "expanded_query": retrieval_query,
        "step_back_question": step_back_question,
        "step_back_answer": step_back_answer,
        "results": results,
    })

    formatted = []
    for i, result in enumerate(results, 1):
        source = result.get("filename", "Unknown")
        page = result.get("page_number", "N/A")
        text = result.get("text", "")
        formatted.append(f"[{i}] {source} (Page {page}):\n{text}")

    parts = []
    if step_back_question:
        parts.append(f"Step-back Question:\n{step_back_question}")
    if step_back_answer:
        parts.append(f"Step-back Answer:\n{step_back_answer}")
    parts.append("Retrieved Chunks:\n" + "\n\n---\n\n".join(formatted))

    return "\n\n".join(parts)
