# Release Notes — v0.1.0 (2026-02-18)

## Highlights
- Executor local seguro via Unix socket.
- Dry-run + confirmação explícita para ações de escrita.
- CLI com intents Linux, histórico persistente e integração com RAG.
- Infra de produção: systemd, sudoers, wrappers, logrotate.

## Added
- Executor com ações estruturadas (`read.*`, `service.control`, `pkg.install`, `ansible.playbook`).
- Segurança com allowlists, ACL policy e verificação de UID/GID.
- Scripts operacionais (deploy, rollback, smoke, post-deploy).
- Documentação extensa para operação e troubleshooting.

## Changed
- CLI ampliado com comandos Linux e confirmação explícita.
- Preview ansible com `--check --diff` e resumo de diff.

## Known Issues
- Testes não executados neste ambiente (pytest ausente).
- Deploy e socket activation ainda não validados em host real.

## Validation
- Final validation report: `docs/17-linux-agent-validation-report.md`
