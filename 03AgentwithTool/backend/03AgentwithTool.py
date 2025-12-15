from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("ARK_API_KEY")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@tool
def to_markdown(text: str) -> str:
    """Convert text to markdown format."""
    return f"```markdown\n{text}\n```"

# Initialize model
model = init_chat_model(
    model=MODEL,
    model_provider="openai",
    api_key=API_KEY,
    base_url=BASE_URL,
    temperature=0.3
)

agent=create_agent(
    model=model,
    tools=[to_markdown],
    system_prompt="""
        You are a cute cat bot that loves to help users. 
        When responding, always use the to_markdown tool to format your answers in markdown. 
        If you don't know the answer, admit it honestly.
        """
    ,
)

# FastAPI App
app = FastAPI(title="Cute Cat Bot API")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Invoke the agent
        result= agent.invoke({
            "messages": [{"role": "user", "content": request.message}]
        })
        # Handle response based on agent type
        if isinstance(result, dict) and "output" in result:
             return ChatResponse(response=result["output"])
        elif isinstance(result, dict) and "messages" in result:
             return ChatResponse(response=result["messages"][-1].content)
        else:
             return ChatResponse(response=str(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)