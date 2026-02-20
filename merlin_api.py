#!/usr/bin/env python3
"""API HTTP local para o Merlin IA conversar com o Electron."""

import argparse
import logging
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

# Importa o core do Merlin (sem modificar nada)
sys.path.insert(0, str(Path(__file__).parent))
from merlin_cli import process_question, load_profile_content
import rag_indexer

app = Flask(__name__)
CORS(app)

# Cache simples pra não reprocessar tudo a cada pergunta
_context_cache = {}


@app.route("/ask", methods=["POST"])
def ask():
    """Recebe pergunta, retorna resposta do Merlin."""
    data = request.get_json() or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Pergunta vazia"}), 400

    try:
        answer = process_question(question)
        _context_cache["last_question"] = question
        _context_cache["last_answer"] = answer

        return jsonify({"answer": answer, "status": "success"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/documents", methods=["GET"])
def list_documents():
    """Lista documentos indexados."""
    try:
        scrolls_dir = Path("scrolls")
        documents = []
        if scrolls_dir.exists():
            for file_path in sorted(scrolls_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in {".txt", ".md", ".pdf"}:
                    continue
                documents.append(
                    {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "indexed": True,
                    }
                )
        return jsonify({"documents": documents})
    except Exception as exc:
        return jsonify({"error": str(exc), "documents": []}), 500


@app.route("/index", methods=["POST"])
def force_index():
    """Força reindexação dos documentos."""
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
    return jsonify({"status": "alive", "rag_loaded": True, "profile_loaded": bool(load_profile_content())})


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
