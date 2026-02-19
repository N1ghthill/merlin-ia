# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-02-18

### Added
- Executor local via Unix socket com ações estruturadas e validação rígida.
- Ações de leitura e escrita com dry-run + confirmação explícita.
- CLI com auto-intents, histórico persistente, logging e indexação RAG opcional.
- Infra completa: systemd unit/socket, logrotate, sudoers, wrappers, playbooks.
- Scripts de deploy, rollback, smoke check e verificação de requisitos.
- Documentação: deploy guide, troubleshooting, release checklist, compatibilidade e relatório final.

### Changed
- CLI do Merlin ampliado com comandos Linux e controle de confirmações.
- Execução de playbook dry-run com `--check --diff` e resumo de diff.

### Security
- Validação de UID/GID via SO_PEERCRED.
- ACL policy baseada em arquivo.
- Wrappers para comandos privilegiados.

### Known Issues
- Testes não executados neste ambiente (pytest ausente).
- Deploy e socket activation não validados em host real.

## [0.1.1] - 2026-02-19

### Added
- Linux Agent validation report (`docs/17-linux-agent-validation-report.md`).
- Linux Agent state snapshot (`docs/linux-agent-state.json`).

### Changed
- Deploy instructions updated (playbooks copied, write actions and Ansible temp guidance).
- Troubleshooting expanded with write/ansible/systemd notes.
