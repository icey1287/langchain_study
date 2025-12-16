# 文档管理功能说明

## 功能概述

SuperAgent 现已集成文档管理功能，支持上传 PDF 和 Word 文档，自动进行向量化处理并存储到 Milvus 数据库中。

## 主要功能

### 1. 文档上传
- 支持格式：PDF（.pdf）、Word（.doc, .docx）
- 自动文本提取和智能分段
- 自动生成向量并存储到 Milvus

### 2. 文档列表
- 查看所有已上传的文档
- 显示文档类型和文本片段数量
- 实时刷新文档列表

### 3. 文档删除
- 删除指定文档
- 同步删除 Milvus 中对应的所有向量数据
- 删除本地存储的文件

## 使用方法

### 前端界面

1. **打开设置页面**
   - 点击左侧边栏的"设置"按钮
   - 进入文档管理界面

2. **上传文档**
   - 点击"选择文件"按钮
   - 选择 PDF 或 Word 文档
   - 点击"开始上传"按钮
   - 等待处理完成（会显示处理进度）

3. **查看文档列表**
   - 设置页面会自动显示已上传的文档
   - 点击"刷新列表"可手动更新

4. **删除文档**
   - 在文档列表中找到要删除的文档
   - 点击右侧的删除按钮（垃圾桶图标）
   - 确认删除操作

### API 端点

#### 1. 获取文档列表
```
GET /documents
```

响应示例：
```json
{
  "documents": [
    {
      "filename": "example.pdf",
      "file_type": "PDF",
      "chunk_count": 25,
      "uploaded_at": null
    }
  ]
}
```

#### 2. 上传文档
```
POST /documents/upload
Content-Type: multipart/form-data

file: <文件数据>
```

响应示例：
```json
{
  "filename": "example.pdf",
  "chunks_processed": 25,
  "message": "成功上传并处理 example.pdf，生成 25 个文本片段"
}
```

#### 3. 删除文档
```
DELETE /documents/{filename}
```

响应示例：
```json
{
  "filename": "example.pdf",
  "chunks_deleted": 25,
  "message": "成功删除文档 example.pdf"
}
```

## 技术实现

### 后端
- **文档处理**：使用 LangChain + Unstructured 库处理 PDF 和 Word 文档
- **文本分段**：RecursiveCharacterTextSplitter 智能分段（支持中文）
- **向量生成**：调用豆包嵌入 API（doubao-embedding-text-240715）
- **向量存储**：Milvus 向量数据库（2560 维向量）

### 前端
- **界面框架**：Vue 3
- **文件上传**：FormData + Fetch API
- **样式设计**：可爱猫咪主题，与整体风格保持一致

## 配置说明

确保 `.env` 文件中包含以下配置：

```env
# Milvus 配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=embeddings_collection

# 豆包 API 配置
BASE_URL=https://ark.cn-beijing.volces.com/api/v3
EMBEDDER=doubao-embedding-text-240715
ARK_API_KEY=your_api_key_here
```

## 数据存储

- **本地文件**：存储在 `SuperAgent/data/` 目录
- **向量数据**：存储在 Milvus 集合中
- **元数据字段**：
  - `id`：主键（自动生成）
  - `embedding`：2560 维向量
  - `text`：文本内容
  - `filename`：文件名
  - `file_type`：文件类型（PDF/Word）
  - `page_number`：页码
  - `chunk_idx`：文本片段索引

## 注意事项

1. **文件大小限制**：根据服务器配置可能有限制
2. **重复文件**：上传同名文件会自动覆盖旧数据
3. **API 额度**：向量生成会调用豆包 API，注意额度限制
4. **处理时间**：大文件可能需要较长处理时间

## 故障排除

### 上传失败
- 检查文件格式是否支持
- 确认 Milvus 服务是否正常运行
- 检查豆包 API 密钥是否有效
- 查看后端日志获取详细错误信息

### 向量查询问题
- 确保文档已成功上传并处理
- 检查 Milvus 集合是否正确初始化
- 验证向量维度是否匹配（2560 维）

### 删除失败
- 确认文件名是否正确
- 检查 Milvus 连接状态
- 查看后端日志获取详细错误信息
