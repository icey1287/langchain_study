import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")

class SectionOutline(BaseModel):
    title: str=Field(description="章节标题")
    key_points: List[str]=Field(description="关键要点")

class ArticleOutline(BaseModel):
    title: str=Field(description="文章主题")
    introduction: str=Field(description="引言")
    sections: List[SectionOutline]=Field(description="文章大纲章节列表")
    conclusion: str=Field(description="结论")

class QualityScore(BaseModel):
    coherence: float=Field(description="连贯性评分，范围0-10",ge=0,le=10)
    relevance: float=Field(description="相关性评分，范围0-10",ge=0,le=10)
    grammar: float=Field(description="语法正确性评分，范围0-10",ge=0,le=10)
    overall: float=Field(description="整体质量评分，范围0-10",ge=0,le=10)
    feedback: Optional[str]=Field(description="质量反馈意见")

class WritingState(TypedDict):
    topic: str                          # 主题
    outline: Optional[ArticleOutline]   # 大纲
    sections_content: List[str]         # 各章节内容
    full_article: str                   # 完整文章
    quality_score: Optional[QualityScore] # 质量评分
    revision_count: int                 # 修订次数
    approved: bool                      # 是否批准
    human_feedback: str                 # 人工反馈

def create_model():
    return init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.7,
    )

def plan_outline(state: WritingState) -> WritingState:
    print(f"\n📋 规划大纲: {state['topic']}")
    model= create_model()
    structured_model=model.with_structured_output(ArticleOutline)
    prompt = f"""请为以下主题创建详细的文章大纲：

      主题：{state['topic']}

      要求：
      1. 创建吸引人的标题
      2. 撰写引言（2-3句）
      3. 设计 3-5 个章节，每个章节列出 2-3 个要点
      4. 撰写结论（2-3句）

      请确保逻辑清晰、结构完整。
      """
    outline=structured_model.invoke(prompt)
    state['outline'] = outline

    print(f"✅ 大纲创建完成")
    print(f"   标题: {outline.title}")
    print(f"   章节数: {len(outline.sections)}")
    return state

def write_sections(state: WritingState) -> WritingState:
    model= create_model()
    for idx, section in enumerate(state['outline'].sections):
        print(f"\n✍️  撰写章节 {idx+1}: {section.title}")
        prompt = f"""请根据以下大纲要点撰写文章章节：

      章节标题：{section.title}
      关键要点：
      {chr(10).join(['- ' + kp for kp in section.key_points])}

      要求：
      1. 每个要点扩展为完整段落
      2. 保持连贯和逻辑性
      3. 使用正式且易懂的语言

      请开始撰写该章节内容。
      """
        section_content = model.invoke(prompt)
        state['sections_content'].append(section_content)
        print(f"✅ 章节 {idx+1} 撰写完成")
    return state

def assemble_article(state: WritingState) -> WritingState:
    print(f"\n📝  组装完整文章")
    model= create_model()
    prompt = f"""请将以下章节内容整合为一篇完整的文章：

      标题：{state['outline'].title}
      引言：{state['outline'].introduction}

      章节内容：
      {chr(10).join([f'章节 {i+1}:\n{content}' for i, content in enumerate(state['sections_content'])])}

      结论：{state['outline'].conclusion}

      要求：
      1. 保持逻辑连贯
      2. 使用过渡句连接各部分
      3. 确保语言流畅且无语法错误

      请开始组装文章。
      """
    full_article = model.invoke(prompt)
    state['full_article'] = full_article
    print(f"✅ 文章组装完成")
    return state

def evaluate_quality(state: WritingState) -> WritingState:
    print(f"\n🔍  评估文章质量")
    model= create_model()
    structured_model=model.with_structured_output(QualityScore)
    prompt = f"""请根据以下标准评估文章质量：

      文章内容：
      {state['full_article']}

      评估标准：
      1. 连贯性（0-10）
      2. 相关性（0-10）
      3. 语法正确性（0-10）
      4. 整体质量（0-10）

      请提供评分和改进建议（如有）。
      """
    quality_score=structured_model.invoke(prompt)
    state['quality_score'] = quality_score

    print(f"✅ 质量评估完成")
    print(f"   整体评分: {quality_score.overall}/10")
    return state

def human_review(state: WritingState) -> WritingState:
    print(f"\n🧑‍💼  等待人工审核...")
    print(f"请审核以下文章内容，并提供反馈意见：\n")
    print(f"标题: {state['outline'].title}\n")
    print(state['full_article'])
    feedback = input("\n请输入您的反馈意见（或按回车跳过）: ")
    state['human_feedback'] = feedback
    state['approved'] = feedback.strip() == ""
    if state['approved']:
        print("✅ 文章已批准，无需修改。")
    else:
        print("❗ 文章未批准，需根据反馈进行修改。")
    return state

def revise_article(state: WritingState) -> WritingState:
    print(f"\n🔄  根据反馈修改文章")
    model= create_model()
    prompt = f"""请根据以下反馈意见修改文章内容：

      原文章内容：
      {state['full_article']}

      反馈意见：
      {state['human_feedback']}

      请对文章进行相应修改。
      """
    revised_article = model.invoke(prompt)
    state['full_article'] = revised_article
    state['revision_count'] += 1
    print(f"✅ 文章修改完成")
    return state

def save_article(state: WritingState):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"article_{timestamp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"标题: {state['outline'].title}\n\n")
        f.write(state['full_article'])
    print(f"\n💾  文章已保存为 {filename}")

def check_quality(state: WritingState) -> str:
    score = state['quality_score'].overall
    if score>=8:
        print("✅ 文章质量符合要求。")
        return "review"
    else:
        print("❗ 文章质量不符合要求，需要修改。")
        return "revise"
    
def check_approval(state: WritingState) -> str:
    if state['approved']:
        print("✅ 文章已获得批准。")
        return "save"
    else:
        print("❗ 文章未获批准，需要修改。")
        return "revise"

def create_writing_workflow():
    workflow=StateGraph(WritingState)
    workflow.add_node("plan", plan_outline)
    workflow.add_node("write", write_sections)
    workflow.add_node("assemble", assemble_article)
    workflow.add_node("evaluate", evaluate_quality)
    workflow.add_node("review", human_review)
    workflow.add_node("revise", revise_article)
    workflow.add_node("save", save_article)

    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "write")
    workflow.add_edge("write", "assemble")
    workflow.add_edge("assemble", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        check_quality,
        {
            "review": "review",
            "revise": "revise"
        }
    )
    workflow.add_conditional_edges(
        "review",
        check_approval,
        {
            "save": "save",
            "revise": "revise"
        }
    )

    workflow.add_edge("revise","assemble")
    workflow.add_edge("save", END)
    return workflow.compile()

def main():
    app=create_writing_workflow()
    topics=[
        "人工智能在医疗领域的应用",
        "气候变化对全球生态系统的影响",
        "远程办公的利与弊分析"
    ]
    for topic in topics:
        print(f"\n================ 开始撰写新文章: {topic} ================\n")
        initial_state: WritingState={
            "topic": topic,
            "outline": None,
            "sections_content": [],
            "full_article": "",
            "quality_score": None,
            "revision_count": 0,
            "approved": False,
            "human_feedback": ""
        }
        result=app.invoke(initial_state)

        print(f"\n\n" + "="*70)
        print("✅ 写作完成！")
        print("="*70)
        print(f"主题: {result['topic']}")
        print(f"标题: {result['outline'].title}")
        print(f"质量评分: {result['quality_score'].overall}/10")
        print(f"修订次数: {result['revision_count']}")
        print(f"状态: {'已发布' if result['approved'] else '待处理'}")

        input("\n按 Enter 继续下一篇...")
        print(f"\n================ 文章撰写完成: {topic} ================\n")

if __name__ == "__main__":
    main()