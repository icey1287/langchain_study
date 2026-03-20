from langsmith import evaluate, Client
from dotenv import load_dotenv
import sys
import os

# 将 backend 路径添加到 sys.path，以便导入你的 RAG 模块
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
from rag_pipeline import run_rag_graph

load_dotenv()

# 1. Create and/or select your dataset
client = Client()
dataset_name = "RAG"

# 2. Define an evaluator
# 这里根据你数据集的参考输出（reference_outputs）来自定义判断标准
def custom_evaluator(run_outputs: dict, reference_outputs: dict) -> bool:

    if isinstance(run_outputs, dict):
        docs = run_outputs.get("docs", [])
    elif hasattr(run_outputs, "outputs") and isinstance(run_outputs.outputs, dict):
        docs = run_outputs.outputs.get("docs", [])
    else:
        docs = []
        
    return len(docs) > 0

# 包装你的 RAG 图作为评估对象
def target_function(inputs: dict) -> dict:
    # 你的数据集中输入必须有 "question" 对应的键
    question = inputs["question"]
    # 真正调用你的 RAG 代码
    result = run_rag_graph(question)
    return result

# 3. Run an evaluation
# For more info on evaluators, see: https://docs.langchain.com/langsmith/evaluation-concepts
evaluate(
    target_function,
    data=dataset_name,
    evaluators=[custom_evaluator],
    experiment_prefix="RAG Pipeline Real Evaluation"
)
