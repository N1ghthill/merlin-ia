import sys
import os
import json
import glob
import hashlib
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Tuple

import ollama
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


MODEL = "qwen2.5:7b"
MAX_TURNS = 15

DEFAULT_TOP_K = 5
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

SYSTEM_PROMPT = """Você é Merlin, o assistente mágico e sábio.

Conhecimento fundamental (sempre verdadeiro):
- RAG significa Retrieval-Augmented Generation (Geração Aumentada por Recuperação).
- RAG NÃO é o sistema Red-Amber-Green.
- Em IA, RAG combina busca de informações relevantes com geração de texto por modelos de linguagem.

Regras de estilo:
- Tom místico, mas acolhedor e direto.
- Use metáforas mágicas ocasionalmente (sem exagerar).
- Se a pergunta for técnica, responda de forma clara e correta.
- Se perceber ambiguidade em um termo, esclareça antes de responder.
- Quando não souber, diga que não sabe e sugira como descobrir.
"""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCROLLS_DIR = os.path.join(BASE_DIR, "scrolls")
HISTORY_PATH = os.path.join(DATA_DIR, "history.jsonl")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
RAG_INDEXER_PATH = os.path.join(BASE_DIR, "rag_indexer.py")

PROFILE_PATH = os.path.join(SCROLLS_DIR, "perfil_usuario.md")

# Manifest incremental de scrolls (para não reindexar tudo sempre)
SCROLLS_MANIFEST_PATH = os.path.join(DATA_DIR, "scrolls_index.json")

# Chunking para indexação de pergaminhos (MVP)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


# ----------------------------
# Utils
# ----------------------------

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SCROLLS_DIR, exist_ok=True)
    os.makedirs(CHROMA_DIR, exist_ok=True)


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def append_jsonl(path: str, obj: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_history(path: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if not os.path.exists(path):
        return messages

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                role = obj.get("role")
                content = obj.get("content")
                if role in {"system", "user", "assistant"} and isinstance(content, str):
                    messages.append({"role": role, "content": content})
            except json.JSONDecodeError:
                continue

    return messages


def trim_context(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    system = [m for m in messages if m["role"] == "system"][:1]
    rest = [m for m in messages if m["role"] != "system"]
    rest = rest[-(MAX_TURNS * 2):]
    return system + rest


def stream_chat(messages: List[Dict[str, str]]) -> str:
    assistant_parts: List[str] = []
    stream = ollama.chat(model=MODEL, messages=messages, stream=True)

    for chunk in stream:
        msg = chunk.get("message") or {}
        content = msg.get("content", "")
        if content:
            assistant_parts.append(content)
            sys.stdout.write(content)
            sys.stdout.flush()

    print()
    return "".join(assistant_parts)


def chunk_text(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks: List[str] = []
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


# ----------------------------
# Perfil canônico (fonte de verdade)
# ----------------------------

def parse_profile(text: str) -> Dict[str, str]:
    profile: Dict[str, str] = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        if k and v:
            profile[k] = v
    return profile


def load_profile() -> Tuple[Dict[str, str], str]:
    if not os.path.exists(PROFILE_PATH):
        return {}, ""
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        raw = f.read()
    return parse_profile(raw), raw


def write_profile(profile: Dict[str, str]) -> None:
    lines = ["# PERFIL_USUARIO"]
    for k in sorted(profile.keys()):
        lines.append(f"{k}: {profile[k]}")
    lines.append("")
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def build_profile_block(profile: Dict[str, str]) -> str:
    if not profile:
        return (
            "PERFIL DO USUÁRIO (vazio):\n"
            "Nenhum dado de perfil foi definido ainda.\n"
            "Se o usuário perguntar sobre nome/preferências, peça para definir via /set.\n"
        )

    lines = [
        "INSTRUÇÃO CRÍTICA (PERFIL):",
        "O bloco abaixo contém FATOS VERDADEIROS do usuário (perfil canônico).",
        "Para perguntas sobre dados pessoais, responda usando estes fatos.",
        "",
        "PERFIL_USUARIO:",
    ]
    for k, v in profile.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    return "\n".join(lines)


def match_profile_question(user_text: str) -> List[str]:
    t = (user_text or "").lower()
    wants: List[str] = []

    if "meu nome" in t or ("qual" in t and "nome" in t):
        wants.append("nome")

    pref_markers = [
        "preferência de desenvolvimento",
        "preferencias de desenvolvimento",
        "minha preferência",
        "minhas preferências",
        "prefiro",
        "preferencia",
        "como eu prefiro",
        "abordagem de desenvolvimento",
    ]
    if any(m in t for m in pref_markers):
        wants.append("preferencia_desenvolvimento")

    seen = set()
    wants = [x for x in wants if not (x in seen or seen.add(x))]
    return wants


def answer_from_profile(profile: Dict[str, str], fields: List[str]) -> str:
    parts = []
    missing = []

    for f in fields:
        if f in profile:
            if f == "nome":
                parts.append(f"Segundo os meus pergaminhos, seu nome é **{profile[f]}**.")
            elif f == "preferencia_desenvolvimento":
                parts.append(
                    "E quanto à sua preferência de desenvolvimento: "
                    f"**{profile[f]}**."
                )
            else:
                parts.append(f"{f}: {profile[f]}")
        else:
            missing.append(f)

    if missing:
        miss_list = ", ".join(missing)
        parts.append(
            f"Não encontrei no seu perfil: {miss_list}. "
            "Você pode definir agora com `/set <chave> <valor>`."
        )

    return "\n\n".join(parts)


# ----------------------------
# RAG (Chroma + Embeddings)
# ----------------------------

def get_collection():
    client = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name="merlin_memory")


def ensure_embedder(embedder_cache: Dict[str, Any]):
    if "embedder" not in embedder_cache:
        embedder_cache["embedder"] = SentenceTransformer(EMBED_MODEL_NAME)
    return embedder_cache["embedder"]


def chroma_add_text(col, embedder, doc_id: str, text: str, metadata: dict) -> None:
    """
    Add idempotente: se id já existe (ou outro erro), ignora no MVP.
    """
    try:
        emb = embedder.encode([text], normalize_embeddings=True).tolist()
        col.add(ids=[doc_id], documents=[text], metadatas=[metadata], embeddings=emb)
    except Exception:
        pass


def index_message_incremental(embedder_cache: Dict[str, Any], role: str, text: str, ts: str) -> None:
    """
    Indexa 1 mensagem imediatamente no Chroma (sem /reindex).
    """
    if role not in {"user", "assistant"}:
        return
    if not isinstance(text, str) or not text.strip():
        return

    col = get_collection()
    embedder = ensure_embedder(embedder_cache)

    h = sha1_text(text)[:12]
    doc_id = f"hist_inc:{ts}:{role}:{h}"

    chroma_add_text(
        col,
        embedder,
        doc_id=doc_id,
        text=text.strip(),
        metadata={"source": "history", "role": role, "ts": ts, "mode": "incremental"},
    )


def build_rag_block(results: Dict[str, Any]) -> str:
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]

    items: List[str] = []
    for doc, meta in zip(documents, metadatas):
        if not isinstance(doc, str) or not doc.strip():
            continue
        if not isinstance(meta, dict):
            meta = {}

        source = meta.get("source", "unknown")
        if source == "history":
            role = meta.get("role", "unknown")
            ts = meta.get("ts", "")
            label = f"histórico ({role}{', ' + ts if ts else ''})"
        elif source == "scroll":
            path = meta.get("path", "scroll")
            label = f"pergaminho ({path})"
        else:
            label = str(source)

        items.append(f"[{label}]\n{doc.strip()}")

    if not items:
        return ""

    return (
        "INSTRUÇÃO (MEMÓRIA RECUPERADA):\n"
        "Use os trechos abaixo como contexto fiel para melhorar sua resposta.\n"
        "Se houver conflito, peça esclarecimento ao usuário.\n\n"
        "MEMÓRIA_RECUPERADA:\n"
        + "\n\n".join(items)
        + "\n"
    )


def retrieve_context(user_query: str, embedder_cache: Dict[str, Any], top_k: int) -> Dict[str, Any]:
    col = get_collection()
    if col.count() == 0:
        return {"documents": [[]], "metadatas": [[]]}

    embedder = ensure_embedder(embedder_cache)
    q_emb = embedder.encode([user_query], normalize_embeddings=True).tolist()

    res = col.query(
        query_embeddings=q_emb,
        n_results=top_k,
        include=["documents", "metadatas"],
    )
    return res


def run_reindex() -> bool:
    """
    Reindex completo (opcional). Incremental cobre histórico.
    """
    if not os.path.exists(RAG_INDEXER_PATH):
        print(f"⚠️  Não encontrei {RAG_INDEXER_PATH}. Crie o rag_indexer.py primeiro.")
        return False

    print("🧠 Reindexando memória (histórico + pergaminhos)...")
    try:
        proc = subprocess.run([sys.executable, RAG_INDEXER_PATH], cwd=BASE_DIR, check=False)
        if proc.returncode == 0:
            print("✅ Reindex concluído.")
            return True
        print(f"⚠️  Reindex terminou com código {proc.returncode}. Veja logs acima.")
        return False
    except Exception as e:
        print(f"⚠️  Falha ao executar reindex: {e}")
        return False


# ----------------------------
# Scrolls incremental
# ----------------------------

def load_scrolls_manifest() -> Dict[str, Any]:
    if not os.path.exists(SCROLLS_MANIFEST_PATH):
        return {"files": {}}
    try:
        with open(SCROLLS_MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"files": {}}
        if "files" not in data or not isinstance(data["files"], dict):
            data["files"] = {}
        return data
    except Exception:
        return {"files": {}}


def save_scrolls_manifest(data: Dict[str, Any]) -> None:
    with open(SCROLLS_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_scroll_files() -> List[str]:
    patterns = [
        os.path.join(SCROLLS_DIR, "**/*.md"),
        os.path.join(SCROLLS_DIR, "**/*.txt"),
    ]
    files: List[str] = []
    for pat in patterns:
        files.extend(glob.glob(pat, recursive=True))
    files = [p for p in files if os.path.isfile(p)]
    return sorted(set(files))


def file_fingerprint(path: str) -> str:
    """
    Fingerprint simples: sha1 do conteúdo (evita depender de mtime).
    """
    with open(path, "rb") as f:
        content = f.read()
    return hashlib.sha1(content).hexdigest()


def index_scrolls_incremental(embedder_cache: Dict[str, Any], include_profile: bool = False) -> Tuple[int, int]:
    """
    Indexa apenas arquivos alterados/novos em scrolls (md/txt).
    Retorna (arquivos_indexados, chunks_adicionados).
    """
    manifest = load_scrolls_manifest()
    known = manifest.get("files", {})

    files = list_scroll_files()
    if not include_profile:
        files = [p for p in files if os.path.abspath(p) != os.path.abspath(PROFILE_PATH)]

    col = get_collection()
    embedder = ensure_embedder(embedder_cache)

    files_indexed = 0
    chunks_added = 0

    for path in files:
        rel = os.path.relpath(path, BASE_DIR)

        try:
            fp = file_fingerprint(path)
        except Exception:
            continue

        prev = known.get(rel)
        if prev and isinstance(prev, dict) and prev.get("fp") == fp:
            continue  # sem mudanças

        # indexar
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception:
            continue

        chunks = chunk_text(text)
        for j, chunk in enumerate(chunks):
            doc_id = f"scr_inc:{rel}:{j}:{sha1_text(chunk)[:12]}"
            chroma_add_text(
                col,
                embedder,
                doc_id=doc_id,
                text=chunk,
                metadata={"source": "scroll", "path": rel, "chunk_index": j, "mode": "incremental"},
            )
            chunks_added += 1

        known[rel] = {"fp": fp, "indexed_at": now_iso(), "chunks": len(chunks)}
        files_indexed += 1

    manifest["files"] = known
    save_scrolls_manifest(manifest)

    return files_indexed, chunks_added


# ----------------------------
# CLI commands
# ----------------------------

def cmd_help():
    print("\nComandos:")
    print("  /help            - mostra comandos")
    print("  /reset           - limpa o contexto em memória (não apaga o arquivo)")
    print("  /stats           - estatísticas do contexto em memória")
    print("  /where           - mostra o caminho do history.jsonl")
    print("  /reindex         - reindex completo (opcional)")
    print("  /index_scrolls   - indexa incrementalmente pergaminhos (md/txt) alterados")
    print("  /rag             - alterna RAG on/off")
    print("  /topk N          - define quantos trechos recuperar (ex: /topk 6)")
    print("  /sources         - mostra as últimas fontes recuperadas")
    print("  /profile         - mostra o perfil canônico atual")
    print("  /set K V         - define campo do perfil (ex: /set nome Irving)")
    print("  exit             - sair\n")


def main():
    ensure_dirs()

    rag_enabled = True
    top_k = DEFAULT_TOP_K
    last_rag_sources: List[str] = []
    embedder_cache: Dict[str, Any] = {}

    # perfil
    profile, raw_profile = load_profile()
    if not os.path.exists(PROFILE_PATH):
        # não sobrescreve se existir, só cria se não existe
        try:
            write_profile({})
        except Exception:
            pass
        profile, raw_profile = load_profile()
    profile_block = build_profile_block(profile)

    history = load_history(HISTORY_PATH)
    has_system = any(m["role"] == "system" for m in history)

    if has_system:
        messages = history
    else:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    messages = trim_context(messages)

    print("🧙 Merlin IA (MVP CLI + JSONL + RAG + PERFIL + INCREMENTAL) — digite 'exit' para sair. (/help para comandos)")
    print(f"📜 Histórico carregado: {sum(1 for m in messages if m['role'] != 'system')} mensagens")
    print(f"🗂️  Arquivo: {HISTORY_PATH}")
    print(f"📚 Pergaminhos: {SCROLLS_DIR}")
    print(f"👤 Perfil: {PROFILE_PATH}")
    print(f"🧠 Chroma: {CHROMA_DIR} | RAG={'ON' if rag_enabled else 'OFF'} | top_k={top_k}")

    if not has_system:
        append_jsonl(HISTORY_PATH, {"ts": now_iso(), "role": "system", "content": SYSTEM_PROMPT})

    # Dica caso Chroma vazio
    try:
        col = get_collection()
        if col.count() == 0:
            print("ℹ️  Memória semântica vazia. Sugestão: /index_scrolls e/ou /reindex uma vez.")
    except Exception:
        print("⚠️  Não consegui abrir o ChromaDB agora. Se persistir, rode /reindex e veja o erro.")

    while True:
        try:
            user = input("\nVocê> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo.")
            break

        if not user:
            continue

        if user.lower() in {"exit", "quit", "sair"}:
            print("Até logo.")
            break

        # comandos
        if user.startswith("/help"):
            cmd_help()
            continue

        if user.startswith("/where"):
            print(HISTORY_PATH)
            continue

        if user.startswith("/profile"):
            prof, raw = load_profile()
            if raw.strip():
                print("\n" + raw.strip() + "\n")
            else:
                print("\n# PERFIL_USUARIO (vazio)\n")
            continue

        if user.startswith("/set "):
            parts = user.split(" ", 2)
            if len(parts) < 3:
                print("Uso: /set chave valor")
                continue
            key = parts[1].strip()
            val = parts[2].strip()
            if not key or not val:
                print("Uso: /set chave valor")
                continue

            prof, _ = load_profile()
            prof[key] = val
            try:
                write_profile(prof)
            except PermissionError as e:
                print(f"⚠️  Sem permissão para escrever em {PROFILE_PATH}.")
                print("    Rode: sudo chown -R $USER:$USER ~/merlin-ia/scrolls && chmod -R u+rwX,go-rwx ~/merlin-ia/scrolls")
                print(f"    Erro: {e}")
                continue

            profile = prof
            profile_block = build_profile_block(profile)
            print(f"✅ Perfil atualizado: {key} = {val}")
            continue

        if user.startswith("/stats"):
            u = sum(1 for m in messages if m["role"] == "user")
            a = sum(1 for m in messages if m["role"] == "assistant")
            s = sum(1 for m in messages if m["role"] == "system")
            print(f"system={s} user={u} assistant={a} total={len(messages)} (MAX_TURNS={MAX_TURNS})")
            print(f"RAG={'ON' if rag_enabled else 'OFF'} top_k={top_k}")
            prof, _ = load_profile()
            print(f"Perfil campos: {len(prof)}")
            try:
                col = get_collection()
                print(f"Chroma itens: {col.count()}")
            except Exception:
                print("Chroma itens: (erro ao ler)")
            if os.path.exists(SCROLLS_MANIFEST_PATH):
                print(f"Scrolls manifest: {SCROLLS_MANIFEST_PATH}")
            continue

        if user.startswith("/reset"):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("✨ Contexto em memória limpo. (Arquivo JSONL preservado)")
            continue

        if user.startswith("/reindex"):
            ok = run_reindex()
            if ok:
                embedder_cache.clear()
            continue

        if user.startswith("/index_scrolls"):
            try:
                files_idx, chunks_add = index_scrolls_incremental(embedder_cache, include_profile=False)
                print(f"✅ Scrolls incremental: {files_idx} arquivo(s) indexado(s), {chunks_add} chunk(s) adicionados.")
            except Exception as e:
                print(f"⚠️  Falha ao indexar scrolls: {e}")
            continue

        if user.startswith("/rag"):
            rag_enabled = not rag_enabled
            print(f"🧠 RAG agora está {'ON' if rag_enabled else 'OFF'}.")
            continue

        if user.startswith("/topk"):
            parts = user.split()
            if len(parts) == 2 and parts[1].isdigit():
                top_k = max(1, min(20, int(parts[1])))
                print(f"🧠 top_k definido para {top_k}.")
            else:
                print("Uso: /topk 5")
            continue

        if user.startswith("/sources"):
            if not last_rag_sources:
                print("Nenhuma fonte recuperada ainda nesta sessão.")
            else:
                print("Últimas fontes recuperadas:")
                for item in last_rag_sources:
                    print(f"- {item}")
            continue

        # -------------
        # fluxo normal
        # -------------

        # salva user (JSONL)
        ts_user = now_iso()
        messages.append({"role": "user", "content": user})
        messages = trim_context(messages)
        append_jsonl(HISTORY_PATH, {"ts": ts_user, "role": "user", "content": user})

        # ✅ incremental: indexa a mensagem user sem /reindex
        try:
            index_message_incremental(embedder_cache, "user", user, ts_user)
        except Exception:
            pass

        # ✅ Interceptar perguntas de perfil e responder determinístico
        requested_fields = match_profile_question(user)
        if requested_fields:
            prof, _ = load_profile()
            reply = answer_from_profile(prof, requested_fields)

            print("Merlin> " + reply)

            ts_assistant = now_iso()
            messages.append({"role": "assistant", "content": reply})
            messages = trim_context(messages)
            append_jsonl(HISTORY_PATH, {"ts": ts_assistant, "role": "assistant", "content": reply})

            # incremental também para a resposta determinística
            try:
                index_message_incremental(embedder_cache, "assistant", reply, ts_assistant)
            except Exception:
                pass

            continue

        # RAG recupera contexto (histórico/pergaminhos gerais)
        rag_block = ""
        last_rag_sources = []
        if rag_enabled:
            try:
                res = retrieve_context(user, embedder_cache, top_k=top_k)
                rag_block = build_rag_block(res)

                metas = (res.get("metadatas") or [[]])[0]
                for meta in metas:
                    if not isinstance(meta, dict):
                        continue
                    if meta.get("source") == "history":
                        role = meta.get("role", "unknown")
                        ts = meta.get("ts", "")
                        last_rag_sources.append(f"histórico ({role}{', ' + ts if ts else ''})")
                    elif meta.get("source") == "scroll":
                        last_rag_sources.append(f"pergaminho ({meta.get('path', 'scroll')})")
                    else:
                        last_rag_sources.append(str(meta.get("source", "unknown")))

                seen = set()
                last_rag_sources = [x for x in last_rag_sources if not (x in seen or seen.add(x))]

            except Exception as e:
                rag_block = ""
                last_rag_sources = []
                print(f"\n⚠️  RAG falhou (seguindo sem RAG): {e}")

        # Monta mensagens desta rodada:
        # 1) system base
        # 2) system perfil (consistência)
        # 3) system memória recuperada (se houver)
        # 4) resto do contexto
        round_messages = list(messages)
        injected_systems = [{"role": "system", "content": profile_block}]
        if rag_block:
            injected_systems.append({"role": "system", "content": rag_block})
        round_messages = [round_messages[0]] + injected_systems + round_messages[1:]

        print("Merlin> ", end="")
        assistant_text = stream_chat(round_messages)

        # salva assistant (JSONL)
        ts_assistant = now_iso()
        messages.append({"role": "assistant", "content": assistant_text})
        messages = trim_context(messages)
        append_jsonl(HISTORY_PATH, {"ts": ts_assistant, "role": "assistant", "content": assistant_text})

        # ✅ incremental: indexa a resposta assistant
        try:
            index_message_incremental(embedder_cache, "assistant", assistant_text, ts_assistant)
        except Exception:
            pass


if __name__ == "__main__":
    main()
