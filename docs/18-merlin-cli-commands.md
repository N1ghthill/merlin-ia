# Merlin CLI — Comandos (Guia Amigável)

Este guia resume os comandos do Merlin CLI e quando usar cada um.

## Pré‑requisitos

Merlin usa Ollama como backend local. Garanta que o Ollama esteja instalado, com o serviço ativo e o modelo baixado. Consulte o `README.md` para os comandos recomendados.

## Início rápido

1. Ative o ambiente:
```bash
cd /home/irving/ruas/repos/merlin-ia
. .venv/bin/activate
```

2. Habilite o executor Linux (para comandos `/linux-*`):
```bash
export MERLIN_ENABLE_EXECUTOR=1
```

3. Opcional (modo seguro, somente leitura):
```bash
export LINUX_READ_ONLY=1
```

4. Abra o CLI:
```bash
python3 merlin_cli.py
```

Atalhos de ergonomia (opcionais):
```bash
ln -s /home/irving/ruas/repos/merlin-ia/scripts/merlin-safe ~/bin/merlin-safe
ln -s /home/irving/ruas/repos/merlin-ia/scripts/merlin-hot ~/bin/merlin-hot
```
`merlin-safe` mantém o executor OFF. `merlin-hot` liga o executor apenas nessa sessão.

## Comandos gerais

- `/help`
  - Mostra todos os comandos disponíveis.

- `/reset`
  - Limpa o contexto em memória (não apaga o histórico em disco).

- `/stats`
  - Mostra estatísticas do contexto, RAG e perfil.

- `/where`
  - Mostra o caminho do `history.jsonl`.

- `exit`
  - Sai do Merlin.

## RAG e Pergaminhos (scrolls)

- `/index_scrolls`
  - Indexa apenas os arquivos `.md/.txt` novos ou alterados em `scrolls/`.

- `/reindex`
  - Reindex completo (histórico + scrolls).

- `/rag`
  - Liga/desliga o RAG.

- `/topk N`
  - Define quantos trechos recuperar (ex: `/topk 6`).

- `/sources`
  - Mostra as fontes recuperadas na sessão.

## Perfil do usuário

- `/profile`
  - Mostra o perfil canônico atual.

- `/set K V`
  - Define um campo no perfil.
  - Exemplo: `/set nome Irving`

## Linux Agent (read-only)

Use estes comandos sem alterar o sistema.
Requer `MERLIN_ENABLE_EXECUTOR=1`.

- `/linux read.os_release {}`
- `/linux read.df {}`
- `/linux read.free {}`
- `/linux read.lsblk {}`
- `/linux read.service_status {"service":"ssh"}`
- `/linux read.journalctl {"service":"ssh","lines":50}`

- `/linux-diagnose <service> [lines]`
  - Exemplo: `/linux-diagnose ssh 50`

## Linux Agent (write actions)

Sempre exigem confirmação explícita.
Requer `MERLIN_ENABLE_EXECUTOR=1`.

- `/linux-install <service> [manager]`
  - Instala pacote e tenta habilitar o serviço (se existir unidade systemd).
  - Se não existir unidade systemd, a etapa de `enable` é ignorada.
  - Exemplo: `/linux-install htop`
  - Exemplo: `/linux-install nginx apt`

- `/linux-exec CONFIRM EXECUTE <request_id>`
  - Executa uma ação pendente.

- `CONFIRM EXECUTE <request_id>`
  - Atalho para executar a ação pendente.

- `/linux-pending`
  - Lista ações pendentes.

- `/linux-pending show <request_id>`
  - Mostra detalhes de uma ação pendente.

- `/linux-history [N]`
  - Mostra histórico das últimas ações.

- `/linux-audit [N]`
  - Mostra as últimas entradas do log de auditoria.

- `/linux-reload-acl`
  - Recarrega a ACL do executor.

- `/linux-lockdown`
  - Limpa pendências, ativa `LINUX_READ_ONLY=1` na sessão e tenta encerrar filhos do executor.

## Auto‑intents (linguagem natural)

Por padrão ficam **desligados** para segurança.

- `/linux-auto on`
  - Habilita detecção de intenções a partir de frases naturais.

- `/linux-auto off`
  - Desabilita a detecção automática.

Exemplo com auto‑intents ligado:
```
Merlin, instala o htop via apt
```

## Segurança (importante)

- Write actions só executam com confirmação explícita.
- Toda execução confirmada é registrada em log de auditoria (padrão: `/var/log/merlin/audit.log`).
- Para travar tudo em modo seguro:
```bash
export LINUX_READ_ONLY=1
```

Se não souber exatamente o que vai acontecer, **não confirme**.
