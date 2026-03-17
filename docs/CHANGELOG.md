# Changelog

As mudanças relevantes do projeto são registradas aqui.

## [0.3.0] - 2026-03-17

### Changed
- Repositório reposicionado publicamente em torno de CLI, API local e Linux Agent.
- README e documentação principal reescritos para avaliação técnica e onboarding.
- Persistência consolidada por `merlin.paths`, com modos `project` e `user`.

### Added
- Guia de arquitetura promovido a documento canônico.
- Índice de documentação com separação entre leitura essencial e histórico do Linux Agent.

### Removed
- Interface Electron e artefatos de UI desktop do escopo ativo do repositório.
- Scripts e referências públicas ligados a packaging desktop.

## [0.2.1] - 2026-02-19

### Added
- Linux Agent validation report (`docs/17-linux-agent-validation-report.md`).
- Linux Agent state snapshot (`docs/linux-agent-state.json`).

### Changed
- Deploy instructions updated (playbooks copied, write actions and Ansible temp guidance).
- Troubleshooting expanded with write/ansible/systemd notes.

## [0.1.0] - 2026-02-18

### Added
- Executor local via Unix socket com ações estruturadas e validação rígida.
- Ações de leitura e escrita com `dry-run` + confirmação explícita.
- CLI com auto-intents, histórico persistente, logging e indexação RAG opcional.
- Infra de operação: systemd, logrotate, sudoers, wrappers e playbooks.

### Security
- Validação de UID/GID via `SO_PEERCRED`.
- ACL policy baseada em arquivo.
- Wrappers para comandos privilegiados.
