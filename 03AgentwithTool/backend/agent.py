from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.tools import tool as lc_tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
try:
    from .tools import get_current_weather
except ImportError:
    from tools import get_current_weather

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")




def create_agent_instance():
    model = init_chat_model(
        model=MODEL,
        model_provider="openai",
        api_key=API_KEY,
        base_url=BASE_URL,
        temperature=0.3,
    )

    # create_agent expects callables or tool objects depending on langchain version
    agent = create_agent(
        model=model,
        tools=[get_current_weather],
        system_prompt=(
            "You are a cute cat bot that loves to help users. "
            "When responding, you may use tools to assist. "
            "If you don't know the answer, admit it honestly."
        ),
    )
    return agent, model


agent, model = create_agent_instance()

MESSAGES = []

def summarize_old_messages(model, messages: list) -> str:
    """将旧消息总结为摘要"""
    # 提取旧对话
    old_conversation = "\n".join([
        f"{'用户' if msg.type == 'human' else 'AI'}: {msg.content}"
        for msg in messages
    ])

    # 生成摘要
    summary_prompt = f"""请总结以下对话的关键信息：

{old_conversation}
总结（包含用户信息、重要事实、待办事项）："""

    summary = model.invoke(summary_prompt).content
    return summary


def chat_with_agent(user_text: str):
    """Invoke the agent with a simple user message and return a string response.

    The wrapper is defensive about the agent return types.
    """
    global MESSAGES
    if len(MESSAGES) > 50:
        # 总结前 40 条消息
        summary = summarize_old_messages(model, MESSAGES[:40])

        # 用摘要替换旧消息
        MESSAGES = [
            SystemMessage(content=f"之前的对话摘要：\n{summary}")
        ] + MESSAGES[40:]

    MESSAGES.append(HumanMessage(content=user_text))
    result = agent.invoke({"messages": MESSAGES})

    response_content = ""
    # Many langchain agent variants return dict/objects; handle common cases
    if isinstance(result, dict):
        if "output" in result:
            response_content = result["output"]
        elif "messages" in result and result["messages"]:
            msg = result["messages"][-1]
            response_content = getattr(msg, "content", str(msg))
        else:
            response_content = str(result)
    elif hasattr(result, "content"):
        response_content = result.content
    else:
        response_content = str(result)
    
    MESSAGES.append(AIMessage(content=response_content))
    return response_content
