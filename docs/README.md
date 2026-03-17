# Documentação do Merlin IA

Este índice separa os documentos essenciais dos materiais de referência e histórico. Se o objetivo for avaliar o projeto rapidamente, não é preciso ler tudo.

## Leitura Recomendada

- [Case técnico](./case.md)
- [Arquitetura](./arquitetura.md)
- [Guia de Instalação](./01-instalacao.md)
- [Como Usar](./02-como-usar.md)
- [API do Merlin IA](./api.md)
- [Comandos do CLI](./18-merlin-cli-commands.md)

## Operação Local

- [Introdução](./00-introducao.md)
- [Ambiente de Referência](./01-ambiente.md)
- [Primeira Invocação](./02-invocacao.md)
- [Erros e Sinais](./03-erros-e-sinais.md)
- [Bootstrap do Zero](./build-do-zero.md)

## Linux Agent: Referência Atual

- [Executor Spec](./04-linux-agent-executor.md)
- [Deploy Guide](./11-linux-agent-deploy.md)
- [Troubleshooting](./12-linux-agent-troubleshooting.md)
- [Compatibility Matrix](./14-linux-agent-compatibility.md)

## Linux Agent: Histórico de Implementação

- [Requirements](./05-linux-agent-requirements.md)
- [Roadmap](./06-linux-agent-roadmap.md)
- [Executor Design](./07-linux-agent-executor-design.md)
- [Implementation Checklist](./08-linux-agent-implementation-checklist.md)
- [Execution Plan](./09-linux-agent-execution-plan.md)
- [Status](./10-linux-agent-status.md)
- [Release Checklist](./13-linux-agent-release-checklist.md)
- [Final Report](./15-linux-agent-final-report.md)
- [Validation Checklist](./16-linux-agent-validation-checklist.md)
- [Validation Report](./17-linux-agent-validation-report.md)
- [Snapshot de estado](./linux-agent-state.json)

Os arquivos acima registram decisões, validações e etapas intermediárias do Linux Agent. Eles não são leitura obrigatória para entender o produto.

## Versionamento

- [CHANGELOG](./CHANGELOG.md)
- [Release Notes](./RELEASE.md)
- [Changelog (alias)](./changelog.md)

## Curadoria

1. Atualize primeiro os documentos essenciais (`README.md`, `docs/README.md`, instalação, uso, API e arquitetura).
2. Use os arquivos de histórico do Linux Agent para registrar detalhes de implementação, não para explicar o produto inteiro.
3. Se uma interface, script ou fluxo sair do projeto, remova a referência pública no mesmo conjunto de mudanças.
