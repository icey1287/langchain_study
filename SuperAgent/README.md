# SuperAgent 项目说明

Agent的项目记录，方便后续持续更新与展示。

## 项目概览
- **核心能力**：
  - LangChain Agent + 自定义工具。
  - 文档上传、切分、向量化后写入 Milvus，支持混合检索（稠密+稀疏）。
  - 会话记忆与摘要，保持长对话上下文。
- **运行形态**：FastAPI 后端 + 纯前端（Vue 3 CDN 单页）+ Milvus 向量库。

## 关键创新点
- **混合检索落地**：稠密向量 + BM25 稀疏向量，Milvus Hybrid Search + RRF 排序，兼顾语义与词匹配。
- **Jina Rerank 接入**：Hybrid/Dense 召回后进行 API 级精排，支持返回 `rerank_score` 并在前端可视化。
- **双向降级**：稀疏生成或 Hybrid 调用失败时自动降级为纯稠密检索，提升稳定性。
- **会话摘要记忆**：自动摘要旧消息并注入系统提示，维持上下文且控制 token。
- **文档处理链路**：上传 → 切分 → 稠密/稀疏向量同步生成 → Milvus 入库，支持重复上传自动清理旧 chunk。
- **工具可扩展**：天气查询示例 + 知识库检索，便于按需增添第三方 API 或企业数据源。
- **RAG 过程可观测**：记录检索、评分、重写与来源信息，前端可展开查看每一步细节。
- **查询重写体系**：Step-Back 与 HyDE 两种扩展方式 + 路由选择，必要时触发重写检索。
- **相关性评分门控**：基于结构化输出的 `grade_documents` 判断是否需要重写检索。

## 未来迭代（Todo Lists）

### RAG部分

1. 文本切分升级为语义分块（Semantic Chunking）————（待定、效果未必比递归字符分块好）
2. 向量嵌入：新增多模态 embedding 能力
3. 检索优化：实现多查询分解 (Multi-query)、子问题检索 ————（效果不太好，往往简单的问题也会复杂化，额外消耗token）
4. 生成优化：适配多文档场景的 refine 策略
5. 搭建 RAG 评估体系
6. Rerank 策略评估（top_k、candidate_k、召回/精排比例）

### 其他能力拓展

1. 开发 SQL assistant Skill
2. 实现暂停功能与人工介入机制
3. 新增问题类型判断，简单问题跳过复杂处理流程
4. 扩展网络搜索能力
5. 支持多步骤规划与任务并行执行
6. 搭建路由器节点，由 LLM 自主判断下一步动作
7. 优化 memory 管理：集成 MemO、LangMem 等方案
8. multi-agent：工具过多，把工具拆分给职责明确的专业化agent，提升工具选择的准确性和整体稳定性
9. 实现流式输出思考过程和最终回答
10. 历史记录会话名称可修改

### 后端服务建设

1. 实现用户注册登录、密码加密、权限管理，基于 sqlalchemy 搭建 ORM 数据库
2. 聊天记录落地数据库，引入 redis 做缓存优化

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

### 1) 项目全链路（端到端）
1. 用户在前端输入问题，调用 `POST /chat`。
2. FastAPI `api.py` 接收请求并进入 `agent.py`。
3. LangChain Agent 根据问题类型决定是否调用工具：
  - 天气问题 → `get_current_weather`
  - 知识问答 → `search_knowledge_base`
4. 若命中知识库工具，进入 `rag_pipeline.py` 执行检索工作流。
5. 检索结果与 RAG Trace 一起返回，Agent 生成最终回答。
6. 后端返回 `response + rag_trace`，前端渲染回答，并在“检索过程”中展示每一步。
7. 同时消息落盘到 `customer_service_history.json`，支持历史会话回放。

### 2) RAG 全链路（重点）
1. **初次召回**：`retrieve_initial`
  - 调用 `retrieve_documents`。
  - 先做 Milvus Hybrid 检索（Dense + Sparse + RRF）。
  - 取更大候选集后走 Jina Rerank 精排。
2. **相关性打分门控**：`grade_documents`
  - 使用结构化输出打分 `yes/no`。
  - `yes` 直接进入生成回答；`no` 进入重写阶段。
3. **查询重写路由**：`rewrite_question`
  - 在 `step_back / hyde / complex` 中选择策略。
  - 生成 `rewrite_query`、`step_back_question`、`hypothetical_doc` 等中间结果。
4. **二次召回**：`retrieve_expanded`
  - 对重写后的查询（或 HyDE 文档）再次检索。
  - 结果去重后返回上下文。
5. **答案生成**：Agent 结合上下文生成最终回答。
6. **可观测追踪**：返回 `rag_trace`，包括
  - 评分结果与路由决策
  - 重写策略与重写内容
  - 初次/二次检索结果
  - 检索分数 `score` 与精排分数 `rerank_score`

### 3) 文档入库链路
1. 前端上传 PDF/Word 到 `POST /documents/upload`。
2. `document_loader.py` 解析文档并切分 chunk。
3. `embedding.py` 生成 Dense 向量与 BM25 Sparse 向量。
4. `milvus_writer.py` 将向量 + 元数据写入 Milvus。
5. 后续检索可直接利用新文档参与召回。

### 4) 会话记忆链路
1. 每轮问答按 `user_id/session_id` 写入本地存储。
2. 当消息过长时触发摘要压缩，保留长期上下文。
3. 前端可通过会话接口读取、删除历史对话。

## 技术栈
- 后端：FastAPI、LangChain Agents、Pydantic、Uvicorn。
- 向量与检索：Milvus（HNSW 稠密索引 + SPARSE_INVERTED_INDEX 稀疏索引）、RRF 融合、Jina Rerank 精排。
- 嵌入与稀疏：自定义 API 调用获取稠密向量；BM25 手写稀疏向量；同时输出双塔特征。
- 前端：Vue 3 (CDN)、marked、highlight.js、纯静态部署。
- 工具链：dotenv 配置、requests、langchain_text_splitters、langchain_community.loaders。

## 环境变量
需在仓库根目录或运行环境配置：
- 模型相关：`ARK_API_KEY`、`MODEL`、`BASE_URL`、`EMBEDDER`
- Rerank 相关：`RERANK_MODEL`、`RERANK_BINDING_HOST`、`RERANK_API_KEY`
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


