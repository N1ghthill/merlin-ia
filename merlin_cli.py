import sys
import os
import json
import glob
import hashlib
import getpass
import signal
import subprocess
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import deque

import ollama
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

try:
    from merlin.tools.linux_tool import LinuxTool
except Exception:
    LinuxTool = None

try:
    from merlin.handlers.linux_handlers import (
        diagnose_service,
        install_and_enable,
        harden_ssh,
        harden_firewall,
        summarize_actions,
    )
except Exception:
    diagnose_service = None
    install_and_enable = None
    harden_ssh = None
    harden_firewall = None
    summarize_actions = None

try:
    from merlin.handlers.linux_intents import detect_intent
except Exception:
    detect_intent = None


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
LINUX_ACTIONS_PATH = os.path.join(DATA_DIR, "linux_actions.jsonl")
LINUX_PENDING_PATH = os.path.join(DATA_DIR, "linux_pending.json")
AUDIT_LOG_DEFAULT_PATH = "/var/log/merlin/audit.log"
AUDIT_LOG_FALLBACK_PATH = os.path.join(DATA_DIR, "merlin_audit.log")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
RAG_INDEXER_PATH = os.path.join(BASE_DIR, "rag_indexer.py")

PROFILE_PATH = os.path.join(SCROLLS_DIR, "perfil_usuario.md")

# Manifest incremental de scrolls (para não reindexar tudo sempre)
SCROLLS_MANIFEST_PATH = os.path.join(DATA_DIR, "scrolls_index.json")

# Chunking para indexação de pergaminhos (MVP)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Cache compartilhado para uso programático (API/integrações).
_PROCESS_EMBEDDER_CACHE: Dict[str, Any] = {}


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


def _touch_path(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8"):
        pass


def resolve_audit_log_path(preferred: str, fallback: str) -> Tuple[str | None, str | None]:
    try:
        _touch_path(preferred)
        return preferred, None
    except Exception as exc:
        try:
            _touch_path(fallback)
            return fallback, f"Sem permissão para usar {preferred}; usando {fallback}."
        except Exception as exc2:
            return None, f"Auditoria indisponível ({exc2})."


def get_confirm_user() -> str:
    try:
        res = subprocess.run(["whoami"], capture_output=True, text=True, check=True)
        name = (res.stdout or "").strip()
        if name:
            return name
    except Exception:
        pass
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def log_audit_event(path: str, event: Dict[str, Any]) -> None:
    payload = dict(event)
    payload.setdefault("ts", now_iso())
    append_jsonl(path, payload)


def audit_execute_results(
    audit_log_path: str,
    request_id: str,
    actions: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    confirmed_by: str,
) -> None:
    for action, res in zip(actions, results):
        payload = {
            "request_id": request_id,
            "confirmed_by": confirmed_by,
            "confirmed_uid": os.geteuid(),
            "confirmed_gid": os.getegid(),
            "action_type": action.get("type"),
            "args": action.get("args", {}),
            "cmd": res.get("cmd"),
            "rc": res.get("rc"),
            "ok": res.get("ok"),
        }
        if "error" in res:
            payload["error"] = res.get("error")
        log_audit_event(audit_log_path, payload)


def _list_processes() -> List[Tuple[int, int, str]]:
    try:
        res = subprocess.run(
            ["ps", "-eo", "pid,ppid,command"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return []
    lines = res.stdout.splitlines()
    items: List[Tuple[int, int, str]] = []
    for line in lines[1:]:
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        cmd = parts[2]
        items.append((pid, ppid, cmd))
    return items


def _find_executor_pids(proc_list: List[Tuple[int, int, str]]) -> List[int]:
    pids: List[int] = []
    try:
        res = subprocess.run(
            ["systemctl", "show", "-p", "MainPID", "--value", "linux-agent.service"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            pid = int(res.stdout.strip() or "0")
            if pid > 0:
                pids.append(pid)
    except Exception:
        pass
    if not pids:
        for pid, _, cmd in proc_list:
            if "executor.executor" in cmd:
                pids.append(pid)
    return sorted(set(pids))


def _collect_descendants(proc_list: List[Tuple[int, int, str]], roots: List[int]) -> List[int]:
    children: List[int] = []
    frontier = set(roots)
    while frontier:
        next_frontier = set()
        for pid, ppid, _ in proc_list:
            if ppid in frontier and pid not in children:
                children.append(pid)
                next_frontier.add(pid)
        frontier = next_frontier
    return children


def kill_executor_children() -> Dict[str, Any]:
    proc_list = _list_processes()
    if not proc_list:
        return {"attempted": 0, "killed": 0, "errors": ["process list unavailable"]}
    exec_pids = _find_executor_pids(proc_list)
    if not exec_pids:
        return {"attempted": 0, "killed": 0, "errors": ["executor not running"]}
    child_pids = _collect_descendants(proc_list, exec_pids)
    killed = 0
    errors: List[str] = []
    for pid in child_pids:
        try:
            os.kill(pid, signal.SIGTERM)
            killed += 1
        except Exception as exc:
            errors.append(f"{pid}: {exc}")
    if child_pids:
        time.sleep(0.5)
        for pid in child_pids:
            try:
                os.kill(pid, 0)
            except Exception:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception as exc:
                errors.append(f"{pid}: {exc}")
    return {"attempted": len(child_pids), "killed": killed, "errors": errors}


def _truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n[truncated at {max_chars} chars]"


def _summarize_linux_result(res: Dict[str, Any], max_chars: int) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for k in ("ok", "dry_run", "rc", "cmd", "error"):
        if k in res:
            summary[k] = res.get(k)
    stdout = res.get("stdout")
    stderr = res.get("stderr")
    if isinstance(stdout, str) and stdout:
        summary["stdout"] = _truncate_text(stdout, max_chars)
    if isinstance(stderr, str) and stderr:
        summary["stderr"] = _truncate_text(stderr, max_chars)
    return summary


_SERVICE_MISSING_PATTERNS = (
    "could not be found",
    "does not exist",
    "unit not found",
    "not-found",
    "no such file or directory",
    "nao encontrado",
    "não encontrado",
    "nao existe",
    "não existe",
)


def _service_unit_missing(res: Dict[str, Any]) -> bool:
    if not isinstance(res, dict):
        return False
    stdout = res.get("stdout") if isinstance(res.get("stdout"), str) else ""
    stderr = res.get("stderr") if isinstance(res.get("stderr"), str) else ""
    text = f"{stdout}\n{stderr}".lower()
    return any(pat in text for pat in _SERVICE_MISSING_PATTERNS)


def _should_skip_service_enable(linux_tool: Any, service: str, request_id: str) -> bool:
    if not service:
        return False
    try:
        res = linux_tool.run(
            "read.service_status",
            args={"service": service},
            dry_run=False,
            request_id=request_id,
        )
    except Exception:
        return False
    return _service_unit_missing(res)


def impact_summary(actions: List[Dict[str, Any]], results: List[Dict[str, Any]], max_cmd_chars: int = 300) -> List[str]:
    lines: List[str] = []
    risk_score = 0
    saw_write = False
    for action in actions:
        action_type = action.get("type", "unknown")
        args = action.get("args", {})
        if action_type == "pkg.install":
            pkgs = args.get("packages", [])
            lines.append(f"Instalar pacotes: {', '.join(pkgs) if pkgs else '(nenhum)'}")
            saw_write = True
            risk_score += 2
        elif action_type == "service.control":
            operation = args.get("operation")
            lines.append(f"Operação de serviço: {args.get('service')} -> {operation}")
            saw_write = True
            if operation in {"restart", "stop", "disable"}:
                risk_score += 2
            else:
                risk_score += 1
        elif action_type == "ansible.playbook":
            lines.append(f"Executar playbook: {args.get('playbook')}")
            saw_write = True
            risk_score += 3
            if any(key in str(args.get("playbook", "")).lower() for key in ("ssh", "firewall", "ufw")):
                risk_score += 2
        else:
            lines.append(f"Ação: {action_type} {args}")

    cmds: List[str] = []
    for res in results:
        if isinstance(res, dict) and res.get("cmd"):
            cmds.append(str(res.get("cmd")))
    if cmds:
        joined = " ; ".join(cmds)
        if len(joined) > max_cmd_chars:
            joined = joined[:max_cmd_chars] + f"... [truncated {max_cmd_chars} chars]"
        lines.append(f"Comandos previstos: {joined}")

    if risk_score <= 1:
        risk_label = "Baixo"
    elif risk_score <= 3:
        risk_label = "Médio"
    else:
        risk_label = "Alto"
    lines.append(f"Risco estimado: {risk_label}")

    if saw_write:
        lines.append("Impacto: pode alterar o sistema (instalações, reinícios, mudanças de configuração).")
    return lines


def diff_summary(results: List[Dict[str, Any]]) -> str | None:
    add = 0
    delete = 0
    for res in results:
        out = res.get("stdout")
        if not isinstance(out, str):
            continue
        for line in out.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            if line.startswith("+"):
                add += 1
            elif line.startswith("-"):
                delete += 1
    if add or delete:
        return f"Preview diff: +{add} -{delete} (ansible --diff)"
    return None


def record_linux_results(
    path: str,
    request_id: str,
    actions: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    mode: str,
    max_chars: int,
) -> None:
    entry = {
        "ts": now_iso(),
        "request_id": request_id,
        "mode": mode,
        "actions": actions,
        "results": [_summarize_linux_result(r, max_chars) for r in results],
    }
    append_jsonl(path, entry)


def format_linux_action_for_index(
    request_id: str,
    mode: str,
    actions: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    max_chars: int,
) -> str:
    lines: List[str] = []
    lines.append("LINUX_ACTION")
    lines.append(f"request_id: {request_id}")
    lines.append(f"mode: {mode}")
    lines.append("")
    lines.append("actions:")
    for action in actions:
        action_type = action.get("type", "unknown")
        args = action.get("args", {})
        lines.append(f"- {action_type} {args}")
    lines.append("")
    lines.append("results:")
    for idx, res in enumerate(results, start=1):
        summary = _summarize_linux_result(res, max_chars)
        lines.append(f"[{idx}] {summary}")
    return "\n".join(lines)


def index_linux_action(
    embedder_cache: Dict[str, Any],
    request_id: str,
    mode: str,
    actions: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
    max_chars: int,
) -> None:
    try:
        text = format_linux_action_for_index(request_id, mode, actions, results, max_chars)
        if not text.strip():
            return
        col = get_collection()
        embedder = ensure_embedder(embedder_cache)
        doc_id = f"linux_action:{request_id}:{sha1_text(text)[:12]}"
        chroma_add_text(
            col,
            embedder,
            doc_id=doc_id,
            text=text,
            metadata={"source": "linux_action", "request_id": request_id, "mode": mode},
        )
    except Exception:
        # Avoid breaking CLI if RAG index fails
        pass


def tail_linux_actions(path: str, n: int = 5) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    dq = deque(maxlen=n)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            dq.append(line)
    items: List[Dict[str, Any]] = []
    for line in dq:
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def load_pending_actions(path: str) -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    now = time.time()
    pending: Dict[str, Dict[str, Any]] = {}
    for req_id, item in data.items():
        if not isinstance(item, dict):
            continue
        expires_at = item.get("expires_at")
        actions = item.get("actions")
        if not isinstance(expires_at, (int, float)):
            continue
        if expires_at <= now:
            continue
        if not isinstance(actions, list) or not actions:
            continue
        pending[str(req_id)] = {
            "actions": actions,
            "expires_at": float(expires_at),
        }
    return pending


def save_pending_actions(path: str, pending: Dict[str, Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)


def cleanup_pending_actions(pending: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    now = time.time()
    return {k: v for k, v in pending.items() if v.get("expires_at", 0) > now}


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


def load_profile_content() -> str:
    """Retorna o conteúdo bruto do perfil canônico."""
    _, raw = load_profile()
    return (raw or "").strip()


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


def process_question(question: str, use_cache: bool = True) -> str:
    """
    Processa uma pergunta e retorna a resposta do Merlin.
    Pensada para reuso via API/integrações, sem alterar o fluxo interativo.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Pergunta vazia")

    ensure_dirs()
    question = question.strip()
    ts_user = now_iso()
    embedder_cache = _PROCESS_EMBEDDER_CACHE if use_cache else {}

    # Mantém comportamento determinístico para perguntas de perfil.
    requested_fields = match_profile_question(question)
    if requested_fields:
        profile, _ = load_profile()
        answer = answer_from_profile(profile, requested_fields)
    else:
        result = {"documents": [[]], "metadatas": [[]]}
        rag_block = ""
        try:
            result = retrieve_context(question, embedder_cache, top_k=DEFAULT_TOP_K)
            rag_block = build_rag_block(result)
        except Exception:
            rag_block = ""

        profile, _ = load_profile()
        profile_block = build_profile_block(profile)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.append({"role": "system", "content": profile_block})
        if rag_block:
            messages.append({"role": "system", "content": rag_block})
        messages.append({"role": "user", "content": question})

        try:
            answer = stream_chat(messages)
        except Exception as exc:
            docs = (result.get("documents") or [[]])[0]
            lines = [
                "Não consegui consultar o modelo local agora, mas recuperei contexto útil:",
            ]
            if docs:
                for doc in docs[:2]:
                    if isinstance(doc, str) and doc.strip():
                        lines.append(f"- {doc.strip()[:220]}")
            else:
                lines.append("- Nenhum trecho recuperado no momento.")
            lines.append(f"Detalhe técnico: {exc}")
            answer = "\n".join(lines)

    ts_assistant = now_iso()

    # Persistência best-effort, sem quebrar o fluxo principal em caso de erro.
    if use_cache:
        try:
            append_jsonl(HISTORY_PATH, {"ts": ts_user, "role": "user", "content": question})
            append_jsonl(HISTORY_PATH, {"ts": ts_assistant, "role": "assistant", "content": answer})
        except Exception:
            pass
        try:
            index_message_incremental(embedder_cache, "user", question, ts_user)
            index_message_incremental(embedder_cache, "assistant", answer, ts_assistant)
        except Exception:
            pass

    return answer


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

def cmd_help(linux_enabled: bool = True):
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
    if linux_enabled:
        print("  /linux TYPE JSON - chama linux_tool em dry-run (ex: /linux read.os_release {})")
        print("  /linux-exec CONFIRM EXECUTE <request_id> - executa ação pendente")
        print("  /linux-pending  - lista ações pendentes")
        print("  /linux-pending show <request_id> - mostra detalhes da ação pendente")
        print("  /linux-diagnose <service> [lines] - diagnóstico rápido (read-only)")
        print("  /linux-install <service> [manager] - instala pacote e habilita serviço se existir (dry-run)")
        print("  /linux-harden [playbook] - hardening via playbook (dry-run)")
        print("  /linux-auto on|off|status - auto-detectar intents Linux no chat")
        print("  /linux-history [N] - mostra últimas ações Linux")
        print("  /linux-audit [N] - mostra últimas entradas de auditoria")
        print("  /linux-reload-acl - recarrega ACL do executor")
        print("  /linux-lockdown - bloqueia execuções, limpa pendências e encerra filhos do executor")
    else:
        print("  (executor Linux desativado; defina MERLIN_ENABLE_EXECUTOR=1 para habilitar /linux-*)")
    print("  exit             - sair\n")


def main():
    ensure_dirs()

    rag_enabled = True
    top_k = DEFAULT_TOP_K
    last_rag_sources: List[str] = []
    embedder_cache: Dict[str, Any] = {}
    linux_executor_enabled = os.getenv("MERLIN_ENABLE_EXECUTOR", "0") in {"1", "true", "yes", "on"}
    linux_tool = LinuxTool() if (LinuxTool and linux_executor_enabled) else None
    pending_linux_actions: Dict[str, Dict[str, Any]] = cleanup_pending_actions(load_pending_actions(LINUX_PENDING_PATH))
    save_pending_actions(LINUX_PENDING_PATH, pending_linux_actions)
    try:
        pending_ttl_seconds = int(os.getenv("LINUX_PENDING_TTL", "300") or "300")
    except ValueError:
        pending_ttl_seconds = 300
    linux_auto = linux_executor_enabled and os.getenv("LINUX_AUTO_INTENTS", "0") in {"1", "true", "yes", "on"}
    linux_log_actions = os.getenv("LINUX_LOG_ACTIONS", "1") in {"1", "true", "yes", "on"}
    try:
        linux_log_max_chars = int(os.getenv("LINUX_LOG_MAX_CHARS", "2000") or "2000")
    except ValueError:
        linux_log_max_chars = 2000
    linux_rag_index = os.getenv("LINUX_RAG_INDEX", "1") in {"1", "true", "yes", "on"}
    try:
        linux_rag_max_chars = int(os.getenv("LINUX_RAG_MAX_CHARS", "2000") or "2000")
    except ValueError:
        linux_rag_max_chars = 2000
    linux_read_only = os.getenv("LINUX_READ_ONLY", "0") in {"1", "true", "yes", "on"}
    try:
        linux_impact_cmd_chars = int(os.getenv("LINUX_IMPACT_CMD_CHARS", "300") or "300")
    except ValueError:
        linux_impact_cmd_chars = 300
    if linux_executor_enabled:
        audit_log_path, audit_log_warning = resolve_audit_log_path(
            os.getenv("MERLIN_AUDIT_LOG", AUDIT_LOG_DEFAULT_PATH),
            AUDIT_LOG_FALLBACK_PATH,
        )
        if audit_log_warning:
            print(f"⚠️  {audit_log_warning}")
    else:
        audit_log_path = None
        audit_log_warning = None

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
    if linux_read_only:
        print("🔒 Linux read-only mode: confirmações bloqueadas (LINUX_READ_ONLY=1)")
    if not linux_executor_enabled:
        print("ℹ️  Executor Linux desativado. Defina MERLIN_ENABLE_EXECUTOR=1 para habilitar /linux-*.")

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
            cmd_help(linux_executor_enabled)
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

        if not linux_executor_enabled and (user.startswith("/linux") or user.upper().startswith("CONFIRM EXECUTE ")):
            print("⚠️  Executor Linux desativado. Defina MERLIN_ENABLE_EXECUTOR=1 para habilitar /linux-*.")
            continue

        if user.startswith("/linux-exec"):
            if linux_tool is None:
                print("⚠️  LinuxTool não disponível (dependências ausentes).")
                continue
            if linux_read_only:
                print("🔒 Linux read-only mode ativo. Execução bloqueada.")
                continue
            if not audit_log_path:
                print("⚠️  Auditoria obrigatória indisponível. Execução bloqueada.")
                continue
            pending_linux_actions = cleanup_pending_actions(pending_linux_actions)
            parts = user.split()
            if len(parts) != 4 or parts[1].upper() != "CONFIRM" or parts[2].upper() != "EXECUTE":
                print("Uso: /linux-exec CONFIRM EXECUTE <request_id>")
                continue
            request_id = parts[3].strip()
            item = pending_linux_actions.get(request_id)
            if not item:
                print("Ação pendente não encontrada ou expirada.")
                continue
            if item.get("expires_at", 0) < time.time():
                pending_linux_actions.pop(request_id, None)
                save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
                print("Ação pendente expirada.")
                continue
            actions = item.get("actions")
            if not actions:
                action_type = item.get("action_type")
                args = item.get("args") or {}
                actions = [{"type": action_type, "args": args}]
            try:
                confirmed_by = get_confirm_user()
                results = []
                for action in actions:
                    action_type = action.get("type")
                    args = action.get("args") or {}
                    if action_type == "service.control" and args.get("operation") == "enable":
                        svc = str(args.get("service", "")).strip()
                        if _should_skip_service_enable(linux_tool, svc, request_id):
                            results.append(
                                {
                                    "ok": True,
                                    "rc": 0,
                                    "stdout": f"Unidade systemd '{svc}' não encontrada; enable ignorado.",
                                    "skipped": True,
                                }
                            )
                            continue
                    res = linux_tool.run(
                        action_type,
                        args=args,
                        dry_run=False,
                        request_id=request_id,
                    )
                    results.append(res)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                try:
                    audit_execute_results(audit_log_path, request_id, actions, results, confirmed_by)
                except Exception as e:
                    print(f"⚠️  Falha ao registrar auditoria: {e}")
                if linux_log_actions:
                    record_linux_results(
                        LINUX_ACTIONS_PATH,
                        request_id,
                        actions,
                        results,
                        mode="execute",
                        max_chars=linux_log_max_chars,
                    )
                if linux_rag_index:
                    index_linux_action(
                        embedder_cache,
                        request_id,
                        "execute",
                        actions,
                        results,
                        max_chars=linux_rag_max_chars,
                    )
            except Exception as e:
                print(f"⚠️  Falha ao executar linux_tool: {e}")
            finally:
                pending_linux_actions.pop(request_id, None)
                save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
            continue

        if user.upper().startswith("CONFIRM EXECUTE "):
            if linux_tool is None:
                print("⚠️  LinuxTool não disponível (dependências ausentes).")
                continue
            if linux_read_only:
                print("🔒 Linux read-only mode ativo. Execução bloqueada.")
                continue
            if not audit_log_path:
                print("⚠️  Auditoria obrigatória indisponível. Execução bloqueada.")
                continue
            pending_linux_actions = cleanup_pending_actions(pending_linux_actions)
            parts = user.split()
            if len(parts) != 3:
                print("Uso: CONFIRM EXECUTE <request_id>")
                continue
            request_id = parts[2].strip()
            item = pending_linux_actions.get(request_id)
            if not item:
                print("Ação pendente não encontrada ou expirada.")
                continue
            if item.get("expires_at", 0) < time.time():
                pending_linux_actions.pop(request_id, None)
                save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
                print("Ação pendente expirada.")
                continue
            actions = item.get("actions") or []
            try:
                confirmed_by = get_confirm_user()
                results = []
                for action in actions:
                    action_type = action.get("type")
                    args = action.get("args") or {}
                    if action_type == "service.control" and args.get("operation") == "enable":
                        svc = str(args.get("service", "")).strip()
                        if _should_skip_service_enable(linux_tool, svc, request_id):
                            results.append(
                                {
                                    "ok": True,
                                    "rc": 0,
                                    "stdout": f"Unidade systemd '{svc}' não encontrada; enable ignorado.",
                                    "skipped": True,
                                }
                            )
                            continue
                    res = linux_tool.run(
                        action_type,
                        args=args,
                        dry_run=False,
                        request_id=request_id,
                    )
                    results.append(res)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                try:
                    audit_execute_results(audit_log_path, request_id, actions, results, confirmed_by)
                except Exception as e:
                    print(f"⚠️  Falha ao registrar auditoria: {e}")
                if linux_log_actions:
                    record_linux_results(
                        LINUX_ACTIONS_PATH,
                        request_id,
                        actions,
                        results,
                        mode="execute",
                        max_chars=linux_log_max_chars,
                    )
                if linux_rag_index:
                    index_linux_action(
                        embedder_cache,
                        request_id,
                        "execute",
                        actions,
                        results,
                        max_chars=linux_rag_max_chars,
                    )
            except Exception as e:
                print(f"⚠️  Falha ao executar linux_tool: {e}")
            finally:
                pending_linux_actions.pop(request_id, None)
                save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
            continue

        if user.startswith("/linux-pending"):
            parts = user.split()
            pending_linux_actions = cleanup_pending_actions(pending_linux_actions)
            save_pending_actions(LINUX_PENDING_PATH, pending_linux_actions)
            now = time.time()
            if len(parts) >= 3 and parts[1] == "show":
                req_id = parts[2].strip()
                item = pending_linux_actions.get(req_id)
                if not item:
                    print("Ação pendente não encontrada ou expirada.")
                    continue
                ttl = int(item.get("expires_at", 0) - now)
                actions = item.get("actions") or []
                print(f"request_id: {req_id} | expira em {ttl}s")
                if summarize_actions:
                    print("Ações:")
                    for line in summarize_actions(actions):
                        print(f"- {line}")
                else:
                    print(f"Ações: {actions}")
                continue

            if not pending_linux_actions:
                print("Nenhuma ação pendente.")
                continue
            print("Ações pendentes:")
            for req_id, item in pending_linux_actions.items():
                ttl = int(item.get("expires_at", 0) - now)
                actions = item.get("actions")
                if actions:
                    print(f"- {req_id} | {len(actions)} ação(ões) | expira em {ttl}s")
                else:
                    print(f"- {req_id} | {item.get('action_type')} | expira em {ttl}s")
            continue

        if user.startswith("/linux-reload-acl"):
            if linux_tool is None:
                print("⚠️  LinuxTool não disponível (dependências ausentes).")
                continue
            try:
                r = linux_tool.session.post(f"{linux_tool.base}/reload_acl", timeout=10)
                print(json.dumps(r.json(), ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"⚠️  Falha ao recarregar ACL: {e}")
            continue

        if user.startswith("/linux-history"):
            parts = user.split()
            n = 5
            if len(parts) >= 2 and parts[1].isdigit():
                n = max(1, min(50, int(parts[1])))
            items = tail_linux_actions(LINUX_ACTIONS_PATH, n=n)
            if not items:
                print("Nenhum histórico encontrado.")
                continue
            for item in items:
                ts = item.get("ts", "")
                mode = item.get("mode", "")
                req = item.get("request_id", "")
                actions = item.get("actions", [])
                print(f"- {ts} | {mode} | {req} | ações={len(actions)}")
            continue

        if user.startswith("/linux-audit"):
            parts = user.split()
            n = 10
            if len(parts) >= 2 and parts[1].isdigit():
                n = max(1, min(200, int(parts[1])))
            if not audit_log_path or not os.path.exists(audit_log_path):
                print("Nenhum log de auditoria encontrado.")
                continue
            items = tail_linux_actions(audit_log_path, n=n)
            if not items:
                print("Nenhum log de auditoria encontrado.")
                continue
            for item in items:
                ts = item.get("ts", "")
                req = item.get("request_id", "")
                by = item.get("confirmed_by", "")
                cmd = item.get("cmd", "")
                action_type = item.get("action_type", "")
                print(f"- {ts} | {req} | {by} | {action_type} | {cmd}")
            continue

        if user.startswith("/linux-lockdown"):
            pending_linux_actions = {}
            save_pending_actions(LINUX_PENDING_PATH, pending_linux_actions)
            linux_read_only = True
            os.environ["LINUX_READ_ONLY"] = "1"
            result = kill_executor_children()
            attempted = result.get("attempted", 0)
            killed = result.get("killed", 0)
            errors = result.get("errors") or []
            print("🔒 Lockdown ativado:")
            print("- Ações pendentes revogadas")
            print("- LINUX_READ_ONLY=1 aplicado nesta sessão")
            print(f"- Processos filhos do executor: {killed}/{attempted} sinalizados")
            if errors:
                print("⚠️  Avisos ao matar processos:")
                for err in errors:
                    print(f"- {err}")
            continue

        if user.startswith("/linux-auto"):
            parts = user.split()
            if len(parts) == 1 or parts[1] == "status":
                print(f"linux_auto={'ON' if linux_auto else 'OFF'}")
                continue
            if parts[1] in {"on", "ON"}:
                linux_auto = True
                print("linux_auto=ON")
                continue
            if parts[1] in {"off", "OFF"}:
                linux_auto = False
                print("linux_auto=OFF")
                continue
            print("Uso: /linux-auto on|off|status")
            continue

        if user.startswith("/linux-diagnose"):
            if linux_tool is None or diagnose_service is None:
                print("⚠️  LinuxTool/handlers não disponíveis.")
                continue
            parts = user.split()
            if len(parts) < 2:
                print("Uso: /linux-diagnose <service> [lines]")
                continue
            service = parts[1].strip()
            lines = 200
            if len(parts) >= 3 and parts[2].isdigit():
                lines = int(parts[2])
            actions = diagnose_service(service, lines=lines)
            if summarize_actions:
                print("Plano:")
                for line in summarize_actions(actions):
                    print(f"- {line}")
            request_id = str(uuid.uuid4())
            results = []
            try:
                for action in actions:
                    res = linux_tool.run(
                        action.get("type"),
                        args=action.get("args") or {},
                        dry_run=True,
                        request_id=request_id,
                    )
                    results.append(res)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                if linux_log_actions:
                    record_linux_results(
                        LINUX_ACTIONS_PATH,
                        request_id,
                        actions,
                        results,
                        mode="diagnose",
                        max_chars=linux_log_max_chars,
                    )
            except Exception as e:
                print(f"⚠️  Falha ao executar diagnóstico: {e}")
            continue

        if user.startswith("/linux-install"):
            if linux_tool is None or install_and_enable is None:
                print("⚠️  LinuxTool/handlers não disponíveis.")
                continue
            parts = user.split()
            if len(parts) < 2:
                print("Uso: /linux-install <service> [manager]")
                continue
            service = parts[1].strip()
            manager = parts[2].strip() if len(parts) >= 3 else "auto"
            actions = install_and_enable(service, manager=manager)
            if summarize_actions:
                print("Plano:")
                for line in summarize_actions(actions):
                    print(f"- {line}")
            request_id = str(uuid.uuid4())
            results = []
            try:
                for action in actions:
                    res = linux_tool.run(
                        action.get("type"),
                        args=action.get("args") or {},
                        dry_run=True,
                        request_id=request_id,
                    )
                    results.append(res)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                if linux_log_actions:
                    record_linux_results(
                        LINUX_ACTIONS_PATH,
                        request_id,
                        actions,
                        results,
                        mode="install_dry_run",
                        max_chars=linux_log_max_chars,
                    )
                print("Impacto estimado:")
                for line in impact_summary(actions, results, max_cmd_chars=linux_impact_cmd_chars):
                    print(f"- {line}")
                diff_line = diff_summary(results)
                if diff_line:
                    print(f"- {diff_line}")
                if any(r.get("dry_run") is True for r in results):
                    pending_linux_actions[request_id] = {
                        "actions": actions,
                        "expires_at": time.time() + pending_ttl_seconds,
                    }
                    save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
                    print(
                        f"✅ Ações pendentes registradas. Para executar use: "
                        f"/linux-exec CONFIRM EXECUTE {request_id} (expira em {pending_ttl_seconds}s)"
                    )
            except Exception as e:
                print(f"⚠️  Falha ao preparar instalação: {e}")
            continue

        if user.startswith("/linux-harden"):
            if linux_tool is None or harden_ssh is None:
                print("⚠️  LinuxTool/handlers não disponíveis.")
                continue
            parts = user.split()
            playbook = parts[1].strip() if len(parts) >= 2 else "ssh_hardening.yml"
            actions = harden_ssh(playbook=playbook)
            if summarize_actions:
                print("Plano:")
                for line in summarize_actions(actions):
                    print(f"- {line}")
            request_id = str(uuid.uuid4())
            results = []
            try:
                for action in actions:
                    res = linux_tool.run(
                        action.get("type"),
                        args=action.get("args") or {},
                        dry_run=True,
                        request_id=request_id,
                    )
                    results.append(res)
                print(json.dumps(results, ensure_ascii=False, indent=2))
                if linux_log_actions:
                    record_linux_results(
                        LINUX_ACTIONS_PATH,
                        request_id,
                        actions,
                        results,
                        mode="harden_dry_run",
                        max_chars=linux_log_max_chars,
                    )
                print("Impacto estimado:")
                for line in impact_summary(actions, results, max_cmd_chars=linux_impact_cmd_chars):
                    print(f"- {line}")
                diff_line = diff_summary(results)
                if diff_line:
                    print(f"- {diff_line}")
                if any(r.get("dry_run") is True for r in results):
                    pending_linux_actions[request_id] = {
                        "actions": actions,
                        "expires_at": time.time() + pending_ttl_seconds,
                    }
                    save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
                    print(
                        f"✅ Ações pendentes registradas. Para executar use: "
                        f"/linux-exec CONFIRM EXECUTE {request_id} (expira em {pending_ttl_seconds}s)"
                    )
            except Exception as e:
                print(f"⚠️  Falha ao preparar hardening: {e}")
            continue

        if user.startswith("/linux"):
            if linux_tool is None:
                print("⚠️  LinuxTool não disponível (dependências ausentes).")
                continue

            parts = user.split(" ", 2)
            if len(parts) < 2:
                print("Uso: /linux TYPE JSON_ARGS")
                print("Ex: /linux read.os_release {}")
                continue

            action_type = parts[1].strip()
            if action_type == "whoami":
                try:
                    res = linux_tool.whoami()
                    print(json.dumps(res, ensure_ascii=False, indent=2))
                except Exception as e:
                    print(f"⚠️  Falha ao chamar linux_tool.whoami: {e}")
                continue

            args = {}
            if len(parts) == 3 and parts[2].strip():
                try:
                    args = json.loads(parts[2].strip())
                    if not isinstance(args, dict):
                        print("JSON_ARGS deve ser um objeto JSON.")
                        continue
                except json.JSONDecodeError:
                    print("JSON_ARGS inválido. Use um objeto JSON, ex: {\"service\":\"nginx\"}")
                    continue

            request_id = str(uuid.uuid4())
            try:
                res = linux_tool.run(action_type, args=args, dry_run=True, request_id=request_id)
                print(json.dumps(res, ensure_ascii=False, indent=2))
                if res.get("dry_run") is True:
                    pending_linux_actions[request_id] = {
                        "actions": [{"type": action_type, "args": args}],
                        "expires_at": time.time() + pending_ttl_seconds,
                    }
                    save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
                    print(
                        f"✅ Ação pendente registrada. Para executar use: "
                        f"/linux-exec CONFIRM EXECUTE {request_id} (expira em {pending_ttl_seconds}s)"
                    )
                    print("Impacto estimado:")
                    for line in impact_summary([{"type": action_type, "args": args}], [res], max_cmd_chars=linux_impact_cmd_chars):
                        print(f"- {line}")
                    diff_line = diff_summary([res])
                    if diff_line:
                        print(f"- {diff_line}")
                if linux_log_actions:
                    record_linux_results(
                        LINUX_ACTIONS_PATH,
                        request_id,
                        [{"type": action_type, "args": args}],
                        [res],
                        mode="manual_dry_run",
                        max_chars=linux_log_max_chars,
                    )
            except Exception as e:
                print(f"⚠️  Falha ao chamar linux_tool: {e}")
            continue

        # Auto-intent detection (optional)
        if linux_auto and linux_tool is not None and detect_intent is not None:
            intent = detect_intent(user)
            if intent:
                itype = intent.get("intent")
                if itype == "diagnose" and diagnose_service:
                    actions = diagnose_service(intent.get("service"), lines=intent.get("lines", 200))
                    if summarize_actions:
                        print("Plano:")
                        for line in summarize_actions(actions):
                            print(f"- {line}")
                    request_id = str(uuid.uuid4())
                    results = []
                    try:
                        for action in actions:
                            res = linux_tool.run(
                                action.get("type"),
                                args=action.get("args") or {},
                                dry_run=True,
                                request_id=request_id,
                            )
                            results.append(res)
                        print(json.dumps(results, ensure_ascii=False, indent=2))
                        if linux_log_actions:
                            record_linux_results(
                                LINUX_ACTIONS_PATH,
                                request_id,
                                actions,
                                results,
                                mode="auto_diagnose",
                                max_chars=linux_log_max_chars,
                            )
                    except Exception as e:
                        print(f"⚠️  Falha ao executar diagnóstico: {e}")
                    continue
                if itype == "install" and install_and_enable:
                    actions = install_and_enable(intent.get("service"), manager=intent.get("manager", "auto"))
                    if summarize_actions:
                        print("Plano:")
                        for line in summarize_actions(actions):
                            print(f"- {line}")
                    request_id = str(uuid.uuid4())
                    results = []
                    try:
                        for action in actions:
                            res = linux_tool.run(
                                action.get("type"),
                                args=action.get("args") or {},
                                dry_run=True,
                                request_id=request_id,
                            )
                            results.append(res)
                        print(json.dumps(results, ensure_ascii=False, indent=2))
                        if linux_log_actions:
                            record_linux_results(
                                LINUX_ACTIONS_PATH,
                                request_id,
                                actions,
                                results,
                                mode="auto_install_dry_run",
                                max_chars=linux_log_max_chars,
                            )
                        print("Impacto estimado:")
                        for line in impact_summary(actions, results, max_cmd_chars=linux_impact_cmd_chars):
                            print(f"- {line}")
                        diff_line = diff_summary(results)
                        if diff_line:
                            print(f"- {diff_line}")
                        if any(r.get("dry_run") is True for r in results):
                            pending_linux_actions[request_id] = {
                                "actions": actions,
                                "expires_at": time.time() + pending_ttl_seconds,
                            }
                            save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
                            print(
                                f"✅ Ações pendentes registradas. Para executar use: "
                                f"/linux-exec CONFIRM EXECUTE {request_id} (expira em {pending_ttl_seconds}s)"
                            )
                    except Exception as e:
                        print(f"⚠️  Falha ao preparar instalação: {e}")
                    continue
                if itype == "harden":
                    target = intent.get("target")
                    if target == "firewall" and harden_firewall:
                        actions = harden_firewall()
                    else:
                        actions = harden_ssh() if harden_ssh else []
                    if actions:
                        if summarize_actions:
                            print("Plano:")
                            for line in summarize_actions(actions):
                                print(f"- {line}")
                        request_id = str(uuid.uuid4())
                        results = []
                        try:
                            for action in actions:
                                res = linux_tool.run(
                                    action.get("type"),
                                    args=action.get("args") or {},
                                    dry_run=True,
                                    request_id=request_id,
                                )
                                results.append(res)
                            print(json.dumps(results, ensure_ascii=False, indent=2))
                            if linux_log_actions:
                                record_linux_results(
                                    LINUX_ACTIONS_PATH,
                                    request_id,
                                    actions,
                                    results,
                                    mode="auto_harden_dry_run",
                                    max_chars=linux_log_max_chars,
                                )
                            print("Impacto estimado:")
                            for line in impact_summary(actions, results, max_cmd_chars=linux_impact_cmd_chars):
                                print(f"- {line}")
                            diff_line = diff_summary(results)
                            if diff_line:
                                print(f"- {diff_line}")
                            if any(r.get("dry_run") is True for r in results):
                                pending_linux_actions[request_id] = {
                                    "actions": actions,
                                    "expires_at": time.time() + pending_ttl_seconds,
                                }
                                save_pending_actions(LINUX_PENDING_PATH, cleanup_pending_actions(pending_linux_actions))
                                print(
                                    f"✅ Ações pendentes registradas. Para executar use: "
                                    f"/linux-exec CONFIRM EXECUTE {request_id} (expira em {pending_ttl_seconds}s)"
                                )
                        except Exception as e:
                            print(f"⚠️  Falha ao preparar hardening: {e}")
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
