# SuperAgent 项目说明

Agent的项目记录，方便后续持续更新与展示。

## 项目概览
- **核心能力**：
  - LangChain Agent + 自定义工具。
  - 文档上传、切分、向量化后写入 Milvus，支持混合检索（稠密+稀疏）。
  - 会话记忆与摘要，保持长对话上下文。
- **运行形态**：FastAPI 后端 + 纯前端（Vue 3 CDN 单页）+ Milvus 向量库。

## 未来迭代（Todo Lists）

### RAG部分
 文本切分升级为语义分块（Semantic Chunking）
 向量嵌入：新增多模态 embedding 能力
 检索优化：实现子问题检索、利用元数据、展示参考文件来源
 生成优化：适配多文档场景的 refine 策略
 新增提问改写功能
 搭建 RAG 评估体系
### 其他能力拓展
 开发 SQL assistant Skill
 实现暂停功能与人工介入机制
 新增问题类型判断，简单问题跳过复杂处理流程
 扩展网络搜索能力
 支持多步骤规划与任务并行执行
 搭建路由器节点，由 LLM 自主判断下一步动作
 优化 memory 管理：集成 MemO、LangMem 等方案
### 后端服务建设
 实现用户注册登录、密码加密、权限管理，基于 sqlalchemy 搭建 ORM 数据库
 聊天记录落地数据库，引入 redis 做缓存优化

## 目录与架构
- 后端：`SuperAgent/backend/`
  - [app.py](backend/app.py)：FastAPI 入口、CORS、静态资源挂载。
  - [api.py](backend/api.py)：聊天、会话管理、文档管理接口。
  - [agent.py](backend/agent.py)：LangChain Agent、会话存储、摘要逻辑。
  - [tools.py](backend/tools.py)：天气查询、知识库检索工具。
  - [embedding.py](backend/embedding.py)：稠密向量 API 调用 + BM25 稀疏向量生成。
  - [document_loader.py](backend/document_loader.py)：PDF/Word 加载与分片。
  - [milvus_writer.py](backend/milvus_writer.py)：向量写入（稠密+稀疏）。
  - [milvus_client.py](backend/milvus_client.py)：Milvus 集合定义、混合检索。
  - [schemas.py](backend/schemas.py)：Pydantic 请求/响应模型。
- 前端：`SuperAgent/frontend/`
  - [index.html](frontend/index.html) + [script.js](frontend/script.js) + [style.css](frontend/style.css)：Vue 3 + marked + highlight.js，提供聊天、历史会话、文档上传/删除界面。
- 数据：`SuperAgent/data/`
  - `customer_service_history.json`：会话落盘存储。
  - `documents/`：上传文档原文件。
- 向量库：Milvus（可由 `docker-compose` 或自建服务提供）。

## 核心流程
- **对话**：前端将用户输入发送到 `/chat` → LangChain Agent 处理 → 自动调用工具（天气/知识库）→ 返回回答并追加到本地消息存储。
- **知识检索**：`search_knowledge_base` 同时生成稠密向量与 BM25 稀疏向量 → Milvus `hybrid_search` 通过 RRF 融合排序，回传片段。
- **文档入库**：上传 PDF/Word → LangChain 文档加载与分片 → 生成稠密+稀疏向量 → 写入 Milvus，并记录元数据（文件名、页码、chunk 序号）。
- **会话记忆**：超过 50 条消息时，对前 40 条做摘要并注入系统消息，保持上下文连续但控制长度。

## 技术栈
- 后端：FastAPI、LangChain Agents、Pydantic、Uvicorn。
- 向量与检索：Milvus（HNSW 稠密索引 + SPARSE_INVERTED_INDEX 稀疏索引）、RRF 融合。
- 嵌入与稀疏：自定义 API 调用获取稠密向量；BM25 手写稀疏向量；同时输出双塔特征。
- 前端：Vue 3 (CDN)、marked、highlight.js、纯静态部署。
- 工具链：dotenv 配置、requests、langchain_text_splitters、langchain_community.loaders。

## 关键创新点
- **混合检索落地**：稠密向量 + BM25 稀疏向量，Milvus Hybrid Search + RRF 排序，兼顾语义与词匹配。
- **双向降级**：稀疏生成或 Hybrid 调用失败时自动降级为纯稠密检索，提升稳定性。
- **会话摘要记忆**：自动摘要旧消息并注入系统提示，维持上下文且控制 token。
- **文档处理链路**：上传 → 切分 → 稠密/稀疏向量同步生成 → Milvus 入库，支持重复上传自动清理旧 chunk。
- **工具可扩展**：天气查询示例 + 知识库检索，便于按需增添第三方 API 或企业数据源。

## 环境变量
需在仓库根目录或运行环境配置：
- 模型相关：`ARK_API_KEY`、`MODEL`、`BASE_URL`、`EMBEDDER`
- Milvus：`MILVUS_HOST`、`MILVUS_PORT`、`MILVUS_COLLECTION`
- 工具：`AMAP_WEATHER_API`、`AMAP_API_KEY`

## API 速览
- `POST /chat`：聊天，入参 `message`、`user_id`、`session_id`。
- `GET /sessions/{user_id}`：列出会话。
- `GET /sessions/{user_id}/{session_id}`：拉取某会话消息。
- `DELETE /sessions/{user_id}/{session_id}`：删除会话。
- `GET /documents`：列出已入库文档及 chunk 数。
- `POST /documents/upload`：上传并向量化 PDF/Word。
- `DELETE /documents/{filename}`：删除指定文档的向量数据。


