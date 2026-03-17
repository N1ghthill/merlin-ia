# Como Usar o Merlin IA

Este guia resume o fluxo de uso diário pelo CLI e pela API local.

## CLI

```bash
source .venv/bin/activate
merlin-ia
```

Comandos úteis:

- `/help`
- `/paths`
- `/profile`
- `/set <chave> <valor>`
- `/index_scrolls`
- `/reindex`

## Documentos locais

1. Descubra o diretório ativo com `/paths`.
2. Coloque seus arquivos `.md` e `.txt` em `scrolls_dir`.
3. Faça a pergunta no CLI.

O Merlin tenta indexar scrolls alterados automaticamente antes da recuperação. Se quiser forçar o processo, use `/index_scrolls` ou `merlin-index`.

## API local

Se você quiser automatizar o uso do Merlin ou preparar a futura interface web, use a API em vez de chamar o core diretamente.

```bash
source .venv/bin/activate
merlin-api --port 3030
```

Exemplo:

```bash
curl -s http://127.0.0.1:3030/health
curl -s http://127.0.0.1:3030/documents
curl -s http://127.0.0.1:3030/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Resuma meus documentos"}'
```

## Linux Agent opcional

Para habilitar o executor Linux:

```bash
export MERLIN_ENABLE_EXECUTOR=1
merlin-ia
```

O fluxo de escrita continua protegido por `dry-run`, confirmação explícita, ACL e auditoria.

## Exemplos de perguntas e comandos

- "Resuma meus documentos sobre Python"
- "O que mudou no meu plano de deploy?"
- "Diagnostique o serviço SSH"
- "Instale o nginx no meu sistema"
- `/linux-diagnose ssh 50`
- `/linux-install nginx`
