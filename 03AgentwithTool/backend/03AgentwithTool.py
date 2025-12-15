from typing import Optional
from dotenv import load_dotenv
import os
import requests
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

AMAP_WEATHER_API=os.getenv("AMAP_WEATHER_API")
AMAP_API_KEY=os.getenv("AMAP_API_KEY")

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@tool
def get_current_weather(location: str,extensions:Optional[str] = "base") -> str:
    """获取指定地区的真实天气数据
    
    Args:
        location (str): 地区名称，例如 "北京"、"上海"、"广州" 等
        extentions (Optional[str]): 可选参数，指定返回的天气数据类型，默认为 "base"。可选值包括 "base"（返回基础天气数据）和 "all"（返回所有天气数据，包括空气质量等）。
    
    Returns:
        str: 返回指定地区的天气信息，格式为字符串。
    
    """
    #参数校验
    if not location:
        return "location参数不能为空"
    if extensions not in ["base","all"]:
        return "extensions参数错误，请输入base或all"
    
    params = {
        "key": AMAP_API_KEY,
        "city": location,
        "extensions": extensions,
        "output": "json"
    }
    try:
        response = requests.get(AMAP_WEATHER_API, params=params, timeout=10)
        response.raise_for_status()  # 抛出 HTTP 错误
        result = response.json()
        
        # 解析 API 响应
        if result.get("status") != "1":
            return f"查询失败：{result.get('info', '未知错误')}"
        
        forecasts = result.get("lives", []) if extensions == "base" else result.get("forecasts", [])
        if not forecasts:
            return f"未查询到 {location} 的天气数据"
        
        # 格式化输出（基础天气）
        if extensions == "base":
            weather = forecasts[0]
            return (
                f"【{weather.get('city', location)} 实时天气】\n"
                f"天气状况：{weather.get('weather', '未知')}\n"
                f"温度：{weather.get('temperature', '未知')}℃\n"
                f"湿度：{weather.get('humidity', '未知')}%\n"
                f"风向：{weather.get('winddirection', '未知')}\n"
                f"风力：{weather.get('windpower', '未知')}级\n"
                f"更新时间：{weather.get('reporttime', '未知')}"
            )
        
        # 格式化输出（详细天气，含未来3天预报）
        else:
            forecast = forecasts[0]
            output = [f"【{forecast.get('city', location)} 天气预报】"]
            output.append(f"更新时间：{forecast.get('reporttime', '未知')}")
            output.append("")
            
            # 今日天气
            today = forecast.get("casts", [])[0]
            output.append("今日天气：")
            output.append(f"  白天：{today.get('dayweather', '未知')}")
            output.append(f"  夜间：{today.get('nightweather', '未知')}")
            output.append(f"  气温：{today.get('nighttemp', '未知')}~{today.get('daytemp', '未知')}℃")
            output.append(f"  风向：{today.get('daywind', '未知')}")
            output.append(f"  风力：{today.get('daypower', '未知')}级")
            
            return "\n".join(output)
    
    except requests.exceptions.Timeout:
        return "错误：请求天气服务超时"
    except requests.exceptions.RequestException as e:
        return f"错误：天气服务请求失败 - {str(e)}"
    except Exception as e:
        return f"错误：解析天气数据失败 - {str(e)}"


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
    tools=[get_current_weather],
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

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path or ""
    if path == "/" or path.endswith((".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Invoke the agent
        result = agent.invoke({
            "messages": [{"role": "user", "content": request.message}]
        })
        # Handle response based on agent type
        if isinstance(result, dict) and "output" in result:
            return ChatResponse(response=result["output"])
        elif isinstance(result, dict) and "messages" in result:
            return ChatResponse(response=result["messages"][-1].content)
        elif hasattr(result, "content"):
            return ChatResponse(response=result.content)
        else:
            return ChatResponse(response=str(result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)