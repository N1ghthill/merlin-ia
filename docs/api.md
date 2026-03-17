# API do Merlin IA

Este guia mostra como usar a API HTTP local do Merlin IA. Ela continua no projeto como contrato de integração e como base para a futura interface web.

## Subir a API

```bash
source .venv/bin/activate
merlin-api --port 3030
```

## Endpoints principais

- `GET /health`: estado da API, readiness e paths ativos.
- `GET /documents`: lista documentos `.md` e `.txt` encontrados em `scrolls_dir`.
- `POST /ask`: recebe `{"question": "..."}` e retorna a resposta do Merlin.
- `POST /index`: dispara reindexação assíncrona do acervo local.

## Exemplos

Saúde:

```bash
curl -s http://127.0.0.1:3030/health
```

Documentos:

```bash
curl -s http://127.0.0.1:3030/documents
```

Pergunta:

```bash
curl -s http://127.0.0.1:3030/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Qual é o contexto dos meus documentos?"}'
```

Reindex:

```bash
curl -s -X POST http://127.0.0.1:3030/index
```

## Observações

- A API escuta em `127.0.0.1` por padrão.
- `/documents` lista somente arquivos `.md` e `.txt`.
- O payload de `health` expõe os caminhos ativos de runtime para facilitar diagnóstico.
- A recomendação é que qualquer frontend futuro use esta API, e não acesso direto ao core Python.
- Se o core Python ou o indexador não estiverem carregáveis, a API sobe mesmo assim e retorna erro explícito em `503`.
