from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户发送的消息内容")
    user_id: str = Field(..., description="用户唯一标识")
    session_id: str = Field(..., description="会话唯一标识，用于关联对话历史")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str = Field(..., description="Agent 返回的回复内容")
    rag_trace: Optional[dict] = Field(default=None, description="RAG 检索追踪信息")


class MessageInfo(BaseModel):
    """单条消息的信息模型"""
    type: str = Field(..., description="消息类型，如 'user' 或 'assistant'")
    content: str = Field(..., description="消息正文内容")
    timestamp: str = Field(..., description="消息时间戳（ISO 格式）")
    rag_trace: Optional[dict] = Field(default=None, description="RAG 追踪信息")


class SessionInfo(BaseModel):
    """会话摘要信息模型"""
    session_id: str = Field(..., description="会话唯一标识")
    updated_at: str = Field(..., description="最后更新时间（ISO 格式）")
    message_count: int = Field(..., ge=0, description="会话中的消息总数")


class SessionListResponse(BaseModel):
    """会话列表响应模型"""
    sessions: list[SessionInfo] = Field(default_factory=list, description="会话信息列表")


class SessionMessagesResponse(BaseModel):
    """会话消息列表响应模型"""
    messages: list[MessageInfo] = Field(default_factory=list, description="该会话的所有消息")


class SessionDeleteResponse(BaseModel):
    """删除会话响应模型"""
    session_id: str = Field(..., description="被删除的会话 ID")
    message: str = Field(..., description="操作结果描述")


class DocumentInfo(BaseModel):
    """文档信息模型"""
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型（如 'pdf', 'docx'）")
    chunk_count: int = Field(..., ge=0, description="该文档被分割的块数量")


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    documents: list[DocumentInfo] = Field(default_factory=list, description="文档信息列表")


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    filename: str = Field(..., description="上传的文件名")
    chunks_processed: int = Field(..., ge=0, description="处理的块数量")
    message: str = Field(..., description="操作结果描述")


class DocumentDeleteResponse(BaseModel):
    """文档删除响应模型"""
    filename: str = Field(..., description="被删除的文件名")
    chunks_deleted: int = Field(..., ge=0, description="删除的块数量")
    message: str = Field(..., description="操作结果描述")
