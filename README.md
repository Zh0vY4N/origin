# 📚 Personal Knowledge Base Q&A Agent

> 基于 RAG（Retrieval-Augmented Generation）架构的个人知识库问答系统。上传文档，用自然语言提问，获取带来源引用的精准回答。

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [API 文档](#api-文档)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [许可协议](#许可协议)

---

## 项目简介

在日常工作和学习中，我们积累了大量文档、笔记和资料。当需要查找某个知识点时，往往需要在多个平台和文件中反复翻找。

本项目通过 **RAG（检索增强生成）** 架构解决了这一痛点：

1. **文档导入** — 支持 PDF、TXT、Markdown 格式的文档上传
2. **智能分块** — 按语义边界将长文档切分为可检索的文本块
3. **向量检索** — 使用 Embedding 模型将文本向量化，通过语义相似度精准匹配
4. **智能回答** — 将检索到的相关上下文交给 LLM，生成结构化、有来源引用的回答

整个流程模拟了"先翻资料，再组织语言回答"的人类思维过程。

---

## 核心特性

| 特性 | 说明 |
|---|---|
| **多格式支持** | 支持 PDF、TXT、Markdown 文档上传 |
| **智能文本分块** | 基于语义边界（段落、句子）的自适应分块策略，避免硬切导致上下文丢失 |
| **本地 Embedding** | 使用 `sentence-transformers` 本地向量化，无需额外 API 调用 |
| **持久化存储** | 基于 ChromaDB 的向量数据库，重启后数据不丢失 |
| **来源引用** | 每次回答附带相关文档来源及相似度评分，可追溯可验证 |
| **多模型支持** | 支持 GPT-4o、GPT-4o Mini、GPT-4 Turbo、GPT-3.5 Turbo 等模型切换 |
| **文档管理** | 支持文档列表查看、单文档删除等管理操作 |
| **现代 UI** | 深色主题、Markdown 渲染、打字动画、拖拽上传 |

---

## 系统架构


用户提问
   │
   ▼
┌─────────────────────────────────────────────┐
│                  FastAPI 后端                │
│                                              │
│  ┌──────────┐    ┌──────────────────────┐   │
│  │ 文档上传  │    │      查询管线         │   │
│  │          │    │                      │   │
│  │ 文本提取  │    │ 1. 问题 Embedding    │   │
│  │    ↓     │    │ 2. 向量相似度检索     │   │
│  │ 智能分块  │    │ 3. 上下文组装        │   │
│  │    ↓     │    │ 4. LLM 生成回答      │   │
│  │ Embedding│    │ 5. 附带来源引用       │   │
│  │    ↓     │    │                      │   │
│  │ 存入DB   │    └──────────┬───────────┘   │
│  └──────────┘               │               │
│         │                   │               │
│         ▼                   ▼               │
│  ┌──────────────────────────────────┐       │
│  │        ChromaDB 向量数据库        │       │
│  │     (持久化存储于 ./chroma_db)    │       │
│  └──────────────────────────────────┘       │
│                                             │
│  ┌──────────────────────────────────┐       │
│  │   sentence-transformers (本地）   │       │
│  │   all-MiniLM-L6-v2 Embedding     │       │
│  └──────────────────────────────────┘       │
└─────────────────────────────────────────────┘
         │
         ▼
   OpenAI API (GPT-4o Mini / GPT-4o / ...)
         │
         ▼
   带来源引用的回答

---

## 技术栈

| 层级 | 技术 | 用途 |
|---|---|---|
| **Web 框架** | FastAPI | 高性能异步 API 服务 |
| **向量数据库** | ChromaDB | 文档向量的持久化存储与检索 |
| **Embedding 模型** | sentence-transformers (all-MiniLM-L6-v2) | 本地文本向量化 |
| **LLM** | OpenAI API (可替换为其他兼容接口) | 基于上下文的回答生成 |
| **PDF 解析** | PyPDF2 | PDF 文本提取 |
| **Markdown 渲染** | marked.js | 前端回答内容渲染 |
| **前端** | 原生 HTML / CSS / JavaScript | 零框架依赖，单文件部署 |

---

## 快速开始

### 环境要求

- Python 3.10+
- pip
- OpenAI API Key

### 安装与启动


# 1. 克隆项目
git clone https://github.com/your-username/knowledge-base-agent.git
cd knowledge-base-agent

# 2. 创建虚拟环境（推荐）
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python app.py


启动成功后会看到：


====================================================
   Personal Knowledge Base Q&A Agent
   → http://localhost:8000
====================================================

[*] Loading embedding model...
[✓] Embedding model ready.


### 首次使用

1. 打开浏览器访问 **http://localhost:8000**
2. 点击右上角 **⚙ 齿轮图标**，填入你的 OpenAI API Key，选择模型，点击保存
3. 在左侧侧边栏 **拖拽或点击上传** 文档（PDF / TXT / MD）
4. 在底部输入框 **输入问题**，按 Enter 发送
5. 等待回答生成，查看附带的 **来源引用**

---

## 使用指南

### 上传文档

- **支持格式**：`.pdf`、`.txt`、`.md`、`.markdown`
- **上传方式**：拖拽文件到上传区域，或点击区域选择文件
- **批量上传**：支持同时选择多个文件
- **上传反馈**：上传成功后会显示文档名、分块数量和处理耗时

### 文档管理

- 左侧边栏展示所有已上传文档及其分块数
- 鼠标悬停文档行，点击右侧 **✕** 可删除单个文档
- 底部状态栏显示文档总数和总分块数

### 提问

- 在底部输入框输入自然语言问题
- 按 **Enter** 发送，**Shift + Enter** 换行
- 系统会自动从知识库中检索相关片段，交给 LLM 生成回答
- 回答下方会显示来源文档标签，悬停可查看匹配的文本片段及相似度评分

### 设置

| 配置项 | 说明 |
|---|---|
| **OpenAI API Key** | 必填，用于调用 LLM 生成回答 |
| **模型** | 可选 GPT-4o Mini（推荐）、GPT-4o、GPT-4 Turbo、GPT-3.5 Turbo |

---

## 项目结构

```
knowledge-base-agent/
│
├── app.py              # 后端主程序（FastAPI + RAG 管线）
├── index.html          # 前端界面（内嵌 CSS 和 JavaScript）
├── requirements.txt    # Python 依赖列表
├── README.md           # 项目说明文档
│
├── uploads/            # 上传的原始文档存储目录（自动创建）
└── chroma_db/          # ChromaDB 持久化数据目录（自动创建）
```

---

## API 文档

服务启动后访问 **http://localhost:8000/docs** 可查看 Swagger 自动生成的交互式 API 文档。

### 接口概览

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/` | 返回前端页面 |
| `POST` | `/api/upload` | 上传文档（multipart/form-data） |
| `GET` | `/api/documents` | 获取所有文档列表 |
| `DELETE` | `/api/documents/{doc_id}` | 删除指定文档 |
| `POST` | `/api/query` | 提问查询 |
| `POST` | `/api/settings` | 更新 API Key 和模型配置 |
| `GET` | `/api/status` | 获取系统状态 |

### 示例：提问

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "这份文档的主要内容是什么？"}'
```

**响应示例：**

```json
{
  "answer": "根据文档内容，主要讨论了以下几个方面：...",
  "sources": [
    {
      "doc_name": "research_paper.pdf",
      "snippet": "本文提出了一种基于深度学习的方法...",
      "relevance": 0.892
    }
  ]
}
```

---

## 配置说明

### 可调参数（app.py 顶部）

| 参数 | 默认值 | 说明 |
|---|---|---|
| `CHUNK_SIZE` | 500 | 每个文本块的最大字符数 |
| `CHUNK_OVERLAP` | 100 | 相邻文本块的重叠字符数 |
| `TOP_K` | 5 | 检索时返回的最相关文本块数量 |
| `EMBEDDING_MODEL_NAME` | all-MiniLM-L6-v2 | Embedding 模型名称 |
| `LLM_MODEL` | gpt-4o-mini | 默认 LLM 模型 |

### Embedding 模型说明

默认使用 `all-MiniLM-L6-v2`，这是一个轻量级的英文 Sentence Embedding 模型（约 80MB），首次运行时会自动从 Hugging Face 下载。

如需更好的中文支持，可替换为：

```python
EMBEDDING_MODEL_NAME = "shibing624/text2vec-base-chinese"
```

> 注意：更换 Embedding 模型后，需要清空 `chroma_db/` 目录并重新上传文档。

### 替换 LLM 提供商

本项目使用 OpenAI SDK，兼容所有 OpenAI API 格式的服务。替换方式：

```python
# app.py 中修改 base_url 即可
openai_client = openai.AsyncOpenAI(
    api_key="your-key",
    base_url="https://your-compatible-api.com/v1"  # 替换为你的服务地址
)
```

兼容服务包括但不限于：Azure OpenAI、DeepSeek、Moonshot、通义千问（兼容模式）等。

---

## 常见问题

### Q: 上传文档后为什么没有回应？

确认已在设置中填入有效的 OpenAI API Key。Embedding 使用本地模型不需要 Key，但 LLM 回答生成需要。

### Q: 支持中文文档吗？

支持。PDF 和 TXT 中的中文文本可以正常提取和检索。Embedding 模型 `all-MiniLM-L6-v2` 以英文为主但也能处理中文，如需更好的中文效果可替换为中文 Embedding 模型（见配置说明）。

### Q: 数据存储在哪里？

- 上传的原始文件存储在 `./uploads/` 目录
- 向量数据存储在 `./chroma_db/` 目录
- 两个目录均在首次运行时自动创建

### Q: 如何清空知识库？

删除 `./chroma_db/` 和 `./uploads/` 目录后重启服务即可。

### Q: Embedding 模型下载失败怎么办？

如果网络环境无法访问 Hugging Face，可以手动下载模型文件，或设置镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### Q: 可以离线使用吗？

Embedding 阶段完全本地运行，无需网络。但 LLM 回答生成需要调用 OpenAI API（或兼容的本地部署服务，如 Ollama + OpenAI 兼容接口）。

---

## 许可协议

MIT License

---

## 致谢

- [ChromaDB](https://github.com/chroma-core/chroma) — 向量数据库
- [sentence-transformers](https://github.com/UKPLab/sentence-transformers) — 文本 Embedding
- [FastAPI](https://github.com/tiangolo/fastapi) — Web 框架
- [marked.js](https://github.com/markedjs/marked) — Markdown 渲染
```
