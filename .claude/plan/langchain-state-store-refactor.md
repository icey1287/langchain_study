# SuperMew 项目重构计划：采用 LangChain 官方 State + Store 架构

## 背景

当前项目的 Agent 实现使用的是**旧版/简化写法**，手动管理对话历史和状态，**未采用 LangChain 官方推荐的架构**。

### 当前问题

| 特性 | 官方推荐 | 当前实现 |
|------|---------|---------|
| 会话状态 (短期记忆) | `checkpointer` | 手动 JSON 文件 (`ConversationStorage`) |
| 长期记忆 | `store` | 未使用 (文档分块用手动 JSON) |
| 状态标识 | `thread_id` | 手动 `user_id` + `session_id` |
| Agent 状态 | 透明可扩展 | 黑盒封装，不可控 |

---

## 目标

将项目从手动状态管理重构为 LangChain 官方推荐的架构：

1. **使用 `checkpointer`**：替代 `ConversationStorage`，实现自动会话状态持久化
2. **使用 `store`**：管理长期记忆（如用户偏好、实体信息）
3. **使用 `thread_id`**：替代手动的 `user_id/session_id` 标识
4. **可选：使用 `StateGraph`**：将 Agent 核心重构为 LangGraph 节点

---

## 重构方案

### 方案一：最小改动（推荐）

保留 `create_agent`，仅添加 `checkpointer` 参数。

#### 步骤 1：修改 `agent.py`

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

# 创建 Checkpointer（短期记忆）
checkpointer = InMemorySaver()

# 创建 Store（长期记忆）
store = InMemoryStore()

# 创建 Agent 时传入
agent = create_agent(
    model=model,
    tools=[get_current_weather, search_knowledge_base],
    system_prompt=system_prompt,
    checkpointer=checkpointer,  # 新增
    store=store,                # 新增
)
```

#### 步骤 2：修改调用方式

```python
# 之前
messages = storage.load(user_id, session_id)
messages.append(HumanMessage(content=user_text))
result = agent.invoke({"messages": messages}, config={"recursion_limit": 8})
storage.save(user_id, session_id, messages)

# 之后
config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}
result = agent.invoke(
    {"messages": [{"role": "user", "content": user_text}]},
    config=config
)
```

#### 步骤 3：清理旧代码

- 删除 `ConversationStorage` 类
- 删除 `storage.save()` / `storage.load()` 调用
- 删除 `data/customer_service_history.json` 相关逻辑

#### 步骤 4：（可选）使用 Store 存储长期记忆

```python
def save_user_memory(user_id: str, memory: dict):
    """存储用户记忆"""
    namespace = ("user_memories", user_id)
    store.put(namespace, str(uuid.uuid4()), memory)

def get_user_memories(user_id: str, query: str = None):
    """获取用户记忆"""
    namespace = ("user_memories", user_id)
    if query:
        return store.search(namespace, query=query)
    return store.list(namespace)
```

---

### 方案二：完整重构（使用 StateGraph）

将 Agent 核心替换为自定义的 LangGraph 节点。

#### 步骤 1：定义 State

```python
from typing import TypedDict
from langgraph.graph import StateGraph, MessagesState, START, END

class AgentState(TypedDict):
    messages: list
    user_id: str
    session_id: str
    context: dict  # RAG 上下文
```

#### 步骤 2：创建 Agent 节点

```python
def agent_node(state: AgentState, runtime: Runtime):
    """Agent 核心节点"""
    # 从 store 获取用户记忆
    memories = runtime.store.search(("user_memories", state["user_id"]))
    
    # 构建系统提示
    system_msg = build_system_prompt(memories)
    
    # 调用模型
    response = model.invoke(
        [{"role": "system", "content": system_msg}] + state["messages"]
    )
    
    return {"messages": [response]}
```

#### 步骤 3：构建图

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

checkpointer = InMemorySaver()
store = InMemoryStore()

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("rag", rag_node)  # RAG 工具节点
graph.add_edge(START, "agent")

compiled = graph.compile(checkpointer=checkpointer, store=store)
```

---

## 实施计划

### 阶段一：最小改动（1-2 天）

1. **Day 1**：
   - 研究 `checkpointer` 和 `store` API
   - 修改 `agent.py` 添加 checkpointer
   - 测试基本对话功能

2. **Day 2**：
   - 迁移现有会话数据（可选）
   - 删除旧的 `ConversationStorage` 代码
   - 端到端测试

### 阶段二：长期记忆（1 天）

3. **Day 3**：
   - 设计用户记忆 schema
   - 实现 `save_user_memory` / `get_user_memories`
   - 在 Agent 中集成记忆检索

### 阶段三：可选重构（2-3 天）

4-5. **Day 4-5**（可选）：
   - 评估是否需要 StateGraph
   - 如需要，完整重构为 LangGraph

---

## 风险与注意事项

### 兼容性

- `create_agent` + `checkpointer` 是**官方支持的组合**，向后兼容
- 流式输出 (`astream`) 需要验证兼容性

### 数据迁移

- 现有 `customer_service_history.json` 需要迁移或废弃
- 建议：先并行运行，确认新方案稳定后再删除旧数据

### 依赖更新

需要确认 `pyproject.toml` 中的依赖版本：

```toml
langchain-core>=0.3
langgraph>=0.2.31
```

---

## 预期收益

| 指标 | 当前 | 重构后 |
|------|------|--------|
| 代码量 | ~100 行存储逻辑 | ~10 行 |
| 会话恢复 | 手动加载/保存 | 自动 (thread_id) |
| 长期记忆 | 无 | 可扩展的 Store |
| 可维护性 | 手动状态，难扩展 | 官方架构，易维护 |
| 官方支持 | 无 | LangChain 官方支持 |

---

## 验收标准

1. ✅ 对话功能正常（流式输出）
2. ✅ 相同 `thread_id` 的请求能恢复会话历史
3. ✅ 长期记忆可存储和检索
4. ✅ 删除了 `ConversationStorage` 相关代码
5. ✅ 端到端测试通过

---

## 相关文档

- [LangChain create_agent + checkpointer](https://docs.langchain.com/oss/python/langchain/short-term-memory)
- [LangGraph Store 持久化](https://docs.langchain.com/oss/python/langgraph/add-memory)
- [LangGraph Checkpointing](https://docs.langchain.com/oss/python/langgraph/persistence)
