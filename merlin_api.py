#!/usr/bin/env python3
"""API HTTP local do Merlin IA, pensada como contrato para integrações e futura interface web."""

import argparse
import logging
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from merlin.paths import describe_paths, scrolls_dir

# Importa o core do Merlin de forma resiliente: a API sobe mesmo se faltar
# alguma dependência Python e retorna erro explícito para o frontend.
APP_ROOT = Path(__file__).parent
sys.path.insert(0, str(APP_ROOT))

_core_import_error = None
_rag_import_error = None

try:
    from merlin_cli import (
        file_fingerprint,
        load_profile_content,
        load_scrolls_manifest,
        process_question,
        relative_scroll_path,
    )
except Exception as exc:
    process_question = None
    _core_import_error = exc

    def load_profile_content():
        return ""

    def load_scrolls_manifest():
        return {"files": {}}

    def file_fingerprint(_path: str) -> str:
        return ""

    def relative_scroll_path(path: str) -> str:
        return path

try:
    import rag_indexer
except Exception as exc:
    rag_indexer = None
    _rag_import_error = exc

app = Flask(__name__)
CORS(app)

# Cache simples pra não reprocessar tudo a cada pergunta
_context_cache = {}


def _exc_message(exc):
    if not exc:
        return None
    return f"{exc.__class__.__name__}: {exc}"


@app.route("/ask", methods=["POST"])
def ask():
    """Recebe pergunta, retorna resposta do Merlin."""
    data = request.get_json() or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Pergunta vazia"}), 400
    if process_question is None:
        return (
            jsonify(
                {
                    "error": "Core do Merlin indisponível no pacote instalado.",
                    "details": _exc_message(_core_import_error),
                }
            ),
            503,
        )

    try:
        answer = process_question(question)
        _context_cache["last_question"] = question
        _context_cache["last_answer"] = answer

        return jsonify({"answer": answer, "status": "success"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/documents", methods=["GET"])
def list_documents():
    """Lista documentos disponíveis em scrolls/ com status real de indexação."""
    try:
        documents_root = Path(scrolls_dir())
        manifest = load_scrolls_manifest()
        known = manifest.get("files", {}) if isinstance(manifest, dict) else {}
        documents = []
        if documents_root.exists():
            for file_path in sorted(documents_root.rglob("*")):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in {".txt", ".md"}:
                    continue
                rel = relative_scroll_path(str(file_path))
                indexed = False
                try:
                    indexed = (known.get(rel) or {}).get("fp") == file_fingerprint(str(file_path))
                except Exception:
                    indexed = False
                documents.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "indexed": indexed,
                    }
                )
        return jsonify({"documents": documents})
    except Exception as exc:
        return jsonify({"error": str(exc), "documents": []}), 500


@app.route("/index", methods=["POST"])
def force_index():
    """Força reindexação dos documentos."""
    if rag_indexer is None:
        return (
            jsonify(
                {
                    "error": "Reindex indisponível (módulo rag_indexer não carregado).",
                    "details": _exc_message(_rag_import_error),
                }
            ),
            503,
        )
    try:
        def run_index():
            rag_indexer.main()

        thread = threading.Thread(target=run_index, daemon=True)
        thread.start()
        return jsonify({"status": "indexing_started"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Endpoint para verificar se a API está viva."""
    return jsonify(
        {
            "status": "alive",
            "core_ready": process_question is not None,
            "rag_ready": rag_indexer is not None,
            "profile_loaded": bool(load_profile_content()),
            "paths": describe_paths(),
            "core_error": _exc_message(_core_import_error),
            "rag_error": _exc_message(_rag_import_error),
        }
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=3030)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    print(f"🧙 Merlin API rodando em http://localhost:{args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
