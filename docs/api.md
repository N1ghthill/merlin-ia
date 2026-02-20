# API do Merlin IA

Este guia mostra como usar a API local do Merlin IA para integrar automações e ferramentas externas com segurança.

## O que este guia cobre

- Como iniciar o serviço da API.
- Como validar se a API está respondendo.
- Exemplos de requisições básicas.

## Passo a passo

1. Ative o ambiente virtual e instale dependências:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-api.txt
```

2. Inicie a API local:

```bash
python merlin_api.py
```

3. Teste um endpoint de saúde (exemplo):

```bash
curl -s http://127.0.0.1:8000/health
```

## Próximos passos

- Combine a API com scripts de automação para tarefas repetitivas.
- Consulte também o guia de uso geral em [Como Usar](./02-como-usar.md).
