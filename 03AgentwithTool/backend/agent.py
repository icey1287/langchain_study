from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.tools import tool as lc_tool
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
    return agent


agent = create_agent_instance()


def chat_with_agent(user_text: str):
    """Invoke the agent with a simple user message and return a string response.

    The wrapper is defensive about the agent return types.
    """
    result = agent.invoke({"messages": [{"role": "user", "content": user_text}]})

    # Many langchain agent variants return dict/objects; handle common cases
    if isinstance(result, dict):
        if "output" in result:
            return result["output"]
        if "messages" in result and result["messages"]:
            msg = result["messages"][-1]
            return getattr(msg, "content", str(msg))
        return str(result)

    # object with content
    if hasattr(result, "content"):
        return result.content

    return str(result)
