"""
Personal Knowledge Base Q&A Agent — RAG Architecture
=====================================================
启动方式:
    1. pip install -r requirements.txt
    2. python app.py
    3. 浏览器打开 http://localhost:8000
    4. 在设置中填入 OpenAI API Key
    5. 上传文档 → 开始提问
"""

import os
import uuid
import time
import asyncio
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
import PyPDF2
import io
import openai

# ============================================================
# 配置
# ============================================================
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CHROMA_DIR = Path("chroma_db")
CHROMA_DIR.mkdir(exist_ok=True)

CHUNK_SIZE = 500        # 每个文本块的字符数
CHUNK_OVERLAP = 100     # 相邻块的重叠字符数
TOP_K = 5               # 检索返回的最相关块数
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ============================================================
# 初始化
# ============================================================
app = FastAPI(title="Knowledge Base Q&A Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ChromaDB 持久化存储
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = chroma_client.get_or_create_collection(
    name="knowledge_base",
    metadata={"hnsw:space": "cosine"},
)

# 本地 Embedding 模型（首次运行自动下载 ~80MB）
print("[*] Loading embedding model...")
embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
print("[✓] Embedding model ready.")

# 线程池（sentence-transformers 是同步的，放到线程中避免阻塞）
executor = ThreadPoolExecutor(max_workers=2)

# OpenAI（动态设置）
openai_client: openai.AsyncOpenAI | None = None
LLM_MODEL = "gpt-4o-mini"


# ============================================================
# 文档处理
# ============================================================
def extract_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        reader = PyPDF2.PdfReader(io.BytesIO(data))
        return "\n".join(
            page.extract_text() or "" for page in reader.pages
        )
    else:  # .txt .md .markdown 等
        return data.decode("utf-8", errors="ignore")


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        # 尽量在句子/段落边界处断开
        if end < len(text):
            for sep in ["\n\n", "\n", "。", ". ", "! ", "? "]:
                idx = text[start:end].rfind(sep)
                if idx > size * 0.3:
                    end = start + idx + len(sep)
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start <= 0 and end >= len(text):
            break
        start = max(start, end - overlap)
    return chunks


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, embed_model.encode, texts)
    return result.tolist()


# ============================================================
# 请求模型
# ============================================================
class QueryRequest(BaseModel):
    question: str

class SettingsRequest(BaseModel):
    api_key: str
    model: str = "gpt-4o-mini"


# ============================================================
# API 端点
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    t0 = time.time()
    data = await file.read()
    text = extract_text(file.filename, data)
    if not text.strip():
        raise HTTPException(400, "无法从文件中提取文本")

    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(400, "未能生成有效文本块")

    embeddings = await get_embeddings(chunks)
    doc_id = uuid.uuid4().hex[:8]
    ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
    metas = [
        {
            "doc_id": doc_id,
            "doc_name": file.filename,
            "chunk_index": i,
            "upload_time": datetime.now().isoformat(),
        }
        for i in range(len(chunks))
    ]
    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metas)

    save_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    save_path.write_bytes(data)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "chunks": len(chunks),
        "characters": len(text),
        "time": round(time.time() - t0, 2),
    }


@app.get("/api/documents")
async def list_documents():
    results = collection.get(include=["metadatas"])
    docs: Dict[str, dict] = {}
    for meta in results["metadatas"]:
        did = meta["doc_id"]
        if did not in docs:
            docs[did] = {
                "doc_id": did,
                "filename": meta["doc_name"],
                "upload_time": meta["upload_time"],
                "chunks": 0,
            }
        docs[did]["chunks"] += 1
    return {"documents": list(docs.values()), "total_chunks": len(results["metadatas"])}


@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    results = collection.get(where={"doc_id": doc_id}, include=["metadatas"])
    if not results["ids"]:
        raise HTTPException(404, "文档不存在")
    collection.delete(ids=results["ids"])
    for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
        f.unlink()
    return {"deleted": len(results["ids"])}


@app.post("/api/query")
async def query_knowledge_base(req: QueryRequest):
    if not openai_client:
        raise HTTPException(400, "请先在设置中填入 OpenAI API Key")

    question = req.question.strip()
    if not question:
        raise HTTPException(400, "问题不能为空")

    count = collection.count()
    if count == 0:
        return {"answer": "知识库为空，请先上传文档。", "sources": []}

    # 检索
    q_emb = await get_embeddings([question])
    results = collection.query(
        query_embeddings=q_emb,
        n_results=min(TOP_K, count),
        include=["documents", "metadatas", "distances"],
    )

    context_chunks = []
    for i in range(len(results["documents"][0])):
        context_chunks.append({
            "text": results["documents"][0][i],
            "doc_name": results["metadatas"][0][i]["doc_name"],
            "distance": results["distances"][0][i],
        })

    context_text = "\n\n---\n\n".join(
        f"[来源: {c['doc_name']}]\n{c['text']}" for c in context_chunks
    )

    system_prompt = (
        "你是一个基于用户个人知识库的智能问答助手。\n"
        "规则：\n"
        "1. 仅根据提供的上下文回答。如果上下文信息不足，请明确说明。\n"
        "2. 回答中引用来源文档名。\n"
        "3. 如果多个文档包含相关信息，请综合整理。\n"
        "4. 使用 Markdown 格式使回答更易读。"
    )
    user_prompt = f"知识库上下文：\n\n{context_text}\n\n---\n\n问题：{question}\n\n请基于以上上下文回答。"

    try:
        resp = await openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        answer = resp.choices[0].message.content
    except Exception as e:
        raise HTTPException(500, f"LLM 调用失败: {e}")

    sources = [
        {
            "doc_name": c["doc_name"],
            "snippet": c["text"][:200] + ("..." if len(c["text"]) > 200 else ""),
            "relevance": round(1 - c["distance"], 3),
        }
        for c in context_chunks
    ]
    return {"answer": answer, "sources": sources}


@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    global openai_client, LLM_MODEL
    openai_client = openai.AsyncOpenAI(api_key=req.api_key)
    LLM_MODEL = req.model
    return {"status": "ok", "model": LLM_MODEL}


@app.get("/api/status")
async def get_status():
    return {
        "api_key_set": openai_client is not None,
        "model": LLM_MODEL,
        "document_count": collection.count(),
        "embedding_model": EMBEDDING_MODEL_NAME,
    }


# ============================================================
# 启动
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 52)
    print("   Personal Knowledge Base Q&A Agent")
    print("   → http://localhost:8000")
    print("=" * 52 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
