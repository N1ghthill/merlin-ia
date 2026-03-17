# Arquitetura do Merlin IA

Merlin IA mantém uma arquitetura deliberadamente simples: um core Python, duas superfícies públicas de entrada e uma camada separada para ações Linux.

## Componentes

- `merlin_cli.py`
  - entrada principal para uso humano
  - concentra chat, perfil, RAG e comandos `/linux-*`

- `merlin_api.py`
  - contrato HTTP local
  - usado por integrações, automações e futura interface web

- `rag_indexer.py`
  - reindexação explícita do acervo local

- `merlin/paths.py`
  - resolve os paths de runtime
  - alterna entre armazenamento `project` e `user`

- `executor/`
  - camada de execução para ações Linux
  - valida argumentos, aplica ACL, usa `dry-run` e registra auditoria

## Fluxos principais

### Perguntas e RAG

```text
CLI/API -> core Python -> recuperação de contexto -> modelo local -> resposta
                           \
                            -> Linux Agent (quando habilitado)
```

### Indexação

- `scrolls_dir` recebe arquivos `.md` e `.txt`
- o manifest registra fingerprint dos arquivos já indexados
- `ChromaDB` armazena os embeddings persistidos
- `merlin-index` força reindexação completa quando necessário

### Ações Linux

- o CLI detecta intent ou recebe comandos `/linux-*`
- o `LinuxTool` conversa com o executor por Unix socket
- ações de escrita exigem `dry-run` e confirmação explícita

## Persistência

- Em um clone Git gravável, o runtime tende a usar `project`, mantendo dados em `./data` e documentos em `./scrolls`.
- Fora desse cenário, usa `user`, com paths XDG em `~/.local/share/merlin-ia` e `~/.local/state/merlin-ia`.
- O comando `/paths` e o endpoint `GET /health` expõem os caminhos efetivamente resolvidos.

## Papel da API

A API permanece no repositório como camada estável para:

- integrações locais
- automações via `curl`
- health checks
- futura interface web

Isso evita duplicar lógica de RAG, perfil, indexação e comandos Linux no cliente.
