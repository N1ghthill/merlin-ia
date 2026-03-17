# Merlin CLI - Comandos

## Início rápido

```bash
source .venv/bin/activate
merlin-ia
```

Para habilitar o executor Linux:

```bash
export MERLIN_ENABLE_EXECUTOR=1
```

Modo seguro:

```bash
export LINUX_READ_ONLY=1
```

## Comandos gerais

- `/help`
- `/reset`
- `/stats`
- `/where`
- `/paths`
- `exit`

## RAG e scrolls

- `/index_scrolls`
  - Indexa arquivos `.md` e `.txt` novos ou alterados.

- `/reindex`
  - Recria o índice completo.

- `/rag`
  - Liga/desliga a recuperação semântica.

- `/topk N`
  - Define quantos trechos recuperar.

- `/sources`
  - Mostra as fontes recuperadas na sessão.

## Perfil

- `/profile`
- `/set K V`

## Linux Agent read-only

- `/linux read.os_release {}`
- `/linux read.df {}`
- `/linux read.free {}`
- `/linux read.lsblk {}`
- `/linux read.service_status {"service":"ssh"}`
- `/linux read.journalctl {"service":"ssh","lines":50}`
- `/linux-diagnose <service> [lines]`

## Linux Agent write actions

- `/linux-install <service> [manager]`
- `/linux-harden [playbook]`
- `/linux-exec CONFIRM EXECUTE <request_id>`
- `CONFIRM EXECUTE <request_id>`
- `/linux-pending`
- `/linux-pending show <request_id>`
- `/linux-history [N]`
- `/linux-audit [N]`
- `/linux-reload-acl`
- `/linux-lockdown`

## Auto-intents

- `/linux-auto on`
- `/linux-auto off`
- `/linux-auto status`

## Notas

- Write actions exigem confirmação explícita.
- O log de auditoria padrão continua em `/var/log/merlin/audit.log`, com fallback para o diretório de estado do usuário.
- `/paths` mostra os diretórios ativos de scrolls, histórico, Chroma e manifest.
