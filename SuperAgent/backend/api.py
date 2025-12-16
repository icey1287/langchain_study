import re
from fastapi import APIRouter, HTTPException
try:
    from .schemas import ChatRequest, ChatResponse, SessionListResponse, SessionInfo, SessionMessagesResponse, MessageInfo
    from .agent import chat_with_agent, storage
except ImportError:
    from schemas import ChatRequest, ChatResponse, SessionListResponse, SessionInfo, SessionMessagesResponse, MessageInfo
    from agent import chat_with_agent, storage

router = APIRouter()


@router.get("/sessions/{user_id}/{session_id}", response_model=SessionMessagesResponse)
async def get_session_messages(user_id: str, session_id: str):
    """获取指定会话的所有消息"""
    try:
        data = storage._load()
        if user_id not in data or session_id not in data[user_id]:
            return SessionMessagesResponse(messages=[])
        
        session_data = data[user_id][session_id]
        messages = []
        for msg_data in session_data.get("messages", []):
            messages.append(MessageInfo(
                type=msg_data["type"],
                content=msg_data["content"],
                timestamp=msg_data["timestamp"]
            ))
        
        return SessionMessagesResponse(messages=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{user_id}", response_model=SessionListResponse)
async def list_sessions(user_id: str):
    """获取用户的所有会话列表"""
    try:
        data = storage._load()
        if user_id not in data:
            return SessionListResponse(sessions=[])
        
        sessions = []
        for session_id, session_data in data[user_id].items():
            sessions.append(SessionInfo(
                session_id=session_id,
                updated_at=session_data.get("updated_at", ""),
                message_count=len(session_data.get("messages", []))
            ))
        
        # 按更新时间倒序排列
        sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return SessionListResponse(sessions=sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        resp = chat_with_agent(request.message, request.user_id, request.session_id)
        return ChatResponse(response=resp)
    except Exception as e:
        message = str(e)
        match = re.search(r"Error code:\s*(\d{3})", message)
        if match:
            code = int(match.group(1))
            if code == 429:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "上游模型服务触发限流/额度限制（429）。请检查账号额度/模型状态。\n"
                        f"原始错误：{message}"
                    ),
                )
            if code in (401, 403):
                raise HTTPException(status_code=code, detail=message)
            raise HTTPException(status_code=code, detail=message)
        raise HTTPException(status_code=500, detail=message)
