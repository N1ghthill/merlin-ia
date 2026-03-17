# Case Técnico - Merlin IA

## Contexto

Merlin IA nasce como um assistente local-first para ambientes Linux em que privacidade, previsibilidade operacional e integração com documentação interna importam mais do que uma interface visual complexa.

## Problema

Times técnicos precisam consultar material privado e automatizar tarefas sem depender de serviços externos, sem espalhar lógica por várias interfaces e sem abrir mão de controle sobre ações no sistema.

## Solução

Um core Python local com:

- CLI
- API HTTP local
- RAG em documentos `Markdown` e `TXT`
- Linux Agent com execução controlada

## Decisões de arquitetura

- `local-first`: conhecimento, histórico e índices permanecem no host.
- `core único`: CLI e API compartilham a mesma lógica de negócio.
- `camada de execução`: ações Linux passam por executor com ACL, `dry-run` e auditoria.
- `paths explícitos`: runtime previsível por `merlin.paths`, com suporte a modo `project` e `user`.

## Relevância técnica do repositório

- mostra um backend Python orientado a produto, não apenas a experimento de IA
- demonstra integração entre RAG, CLI, API local e automação operacional
- documenta trade-offs e evolução do Linux Agent sem esconder o histórico
- mantém suíte de testes e fluxo de validação explícitos

## Escopo atual

- interfaces públicas atuais: CLI e API local
- plataforma alvo: Linux
- evolução prevista: interface web apoiada na API local já existente
