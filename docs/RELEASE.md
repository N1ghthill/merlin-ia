# Release Notes — v0.3.0 (2026-03-17)

## Highlights

- Projeto reposicionado em torno de CLI, API local e Linux Agent.
- Interface Electron e materiais de packaging desktop removidos do escopo ativo.
- Documentação principal reescrita para leitura rápida, onboarding e avaliação técnica.

## Changed

- `README.md` e `docs/README.md` agora expõem somente as superfícies atuais do projeto.
- A API local permanece explicitamente como contrato da futura interface web.
- A persistência documentada acompanha o comportamento real de `merlin.paths`, com modos `project` e `user`.

## Removed

- `electron/`, `electron-app/`, ícones e screenshots antigos.
- Scripts e referências públicas ligados a build do app desktop.

## Recommended Validation

- `make test`
- `make compile`
- `merlin-ia`
- `merlin-api --port 3030`
- `merlin-index`

## Related Docs

- `docs/arquitetura.md`
- `docs/04-linux-agent-executor.md`
- `docs/17-linux-agent-validation-report.md`
