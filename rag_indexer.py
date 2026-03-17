import os
import json
import glob
import hashlib
from types import SimpleNamespace
from datetime import datetime
from typing import List, Dict, Tuple

try:
    import chromadb
    from chromadb.config import Settings
    _CHROMA_IMPORT_ERROR = None
except Exception as exc:
    chromadb = SimpleNamespace(PersistentClient=None)

    def Settings(**kwargs):
        return kwargs

    _CHROMA_IMPORT_ERROR = exc

try:
    from sentence_transformers import SentenceTransformer
    _EMBED_IMPORT_ERROR = None
except Exception as exc:
    SentenceTransformer = None
    _EMBED_IMPORT_ERROR = exc

from merlin.paths import PROJECT_ROOT, chroma_dir, data_dir, history_path, scrolls_dir


BASE_DIR = str(PROJECT_ROOT)
DATA_DIR = str(data_dir())
SCROLLS_DIR = str(scrolls_dir())
HISTORY_PATH = str(history_path())
CHROMA_DIR = str(chroma_dir())

EMBED_MODEL_NAME = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# chunking simples e robusto para MVP
CHUNK_SIZE = 1000       # caracteres
CHUNK_OVERLAP = 150     # caracteres


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    os.makedirs(SCROLLS_DIR, exist_ok=True)
    os.makedirs(CHROMA_DIR, exist_ok=True)


def chunk_text(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + CHUNK_SIZE)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def read_history_messages(path: str) -> List[Dict]:
    msgs = []
    if not os.path.exists(path):
        return msgs
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            role = obj.get("role")
            content = obj.get("content")
            ts = obj.get("ts")
            if role in {"user", "assistant"} and isinstance(content, str):
                msgs.append({"role": role, "content": content, "ts": ts})
    return msgs


def read_scroll_files(scrolls_dir: str) -> List[Tuple[str, str]]:
    files = []
    patterns = [
        os.path.join(scrolls_dir, "**/*.md"),
        os.path.join(scrolls_dir, "**/*.txt"),
    ]
    for pat in patterns:
        for path in glob.glob(pat, recursive=True):
            if os.path.isfile(path):
                files.append(path)

    out = []
    for path in sorted(set(files)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                out.append((path, f.read()))
        except UnicodeDecodeError:
            # ignora arquivos com encoding inesperado no MVP
            continue
    return out


def relative_scroll_path(path: str) -> str:
    rel = os.path.relpath(path, SCROLLS_DIR)
    return os.path.join("scrolls", rel).replace("\\", "/")


def get_collection():
    if not callable(getattr(chromadb, "PersistentClient", None)):
        raise RuntimeError(f"ChromaDB indisponível: {_CHROMA_IMPORT_ERROR}")
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name="merlin_memory")


def reset_collection(col) -> None:
    try:
        payload = col.get()
    except Exception:
        payload = {}
    ids = list(payload.get("ids") or [])
    if not ids:
        return
    try:
        col.delete(ids=ids)
    except Exception:
        pass


def main():
    ensure_dirs()
    print(f"🧠 Merlin RAG Indexer — {now_iso()}")
    print(f"📦 Embedding model: {EMBED_MODEL_NAME}")
    print(f"🗂️  Chroma dir: {CHROMA_DIR}")

    if SentenceTransformer is None:
        raise RuntimeError(f"SentenceTransformer indisponível: {_EMBED_IMPORT_ERROR}")
    embedder = SentenceTransformer(EMBED_MODEL_NAME)
    col = get_collection()
    reset_collection(col)

    # 1) Indexar histórico
    history = read_history_messages(HISTORY_PATH)
    hist_docs = 0
    hist_chunks = 0

    for i, msg in enumerate(history):
        role = msg["role"]
        content = msg["content"]
        ts = msg.get("ts") or ""
        # chunk por mensagem (para MVP)
        for j, chunk in enumerate(chunk_text(content)):
            doc_id = f"hist:{i}:{j}:{sha1(role + '|' + chunk)}"
            try:
                emb = embedder.encode([chunk], normalize_embeddings=True).tolist()
                col.add(
                    ids=[doc_id],
                    documents=[chunk],
                    metadatas=[{
                        "source": "history",
                        "role": role,
                        "ts": ts,
                        "msg_index": i,
                        "chunk_index": j,
                    }],
                    embeddings=emb,
                )
                hist_chunks += 1
            except Exception:
                pass
        hist_docs += 1

    # 2) Indexar pergaminhos (txt/md)
    scrolls = read_scroll_files(SCROLLS_DIR)
    scr_files = 0
    scr_chunks = 0

    for path, text in scrolls:
        rel = relative_scroll_path(path)
        scr_files += 1
        for j, chunk in enumerate(chunk_text(text)):
            doc_id = f"scr:{rel}:{j}:{sha1(chunk)}"
            try:
                emb = embedder.encode([chunk], normalize_embeddings=True).tolist()
                col.add(
                    ids=[doc_id],
                    documents=[chunk],
                    metadatas=[{
                        "source": "scroll",
                        "path": rel,
                        "chunk_index": j,
                    }],
                    embeddings=emb,
                )
                scr_chunks += 1
            except Exception:
                pass

    count = col.count()
    print(f"✅ Indexação concluída.")
    print(f"   Histórico: {hist_docs} msgs → {hist_chunks} chunks adicionados")
    print(f"   Pergaminhos: {scr_files} arquivos → {scr_chunks} chunks adicionados")
    print(f"   Total na coleção: {count} itens")


if __name__ == "__main__":
    main()
