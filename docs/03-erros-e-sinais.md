# Erros e Sinais

Este guia resume sinais comuns de falha e um fluxo de diagnóstico rápido para resolver problemas sem comprometer o ambiente.

## Sinais comuns

- Falha ao conectar no Ollama.
- Erro de dependência Python ausente.
- Comandos `/linux-*` não executam por falta de executor/socket.

## Passo a passo de diagnóstico

1. Confirme que o ambiente virtual está ativo e dependências instaladas:

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

2. Verifique o Ollama:

```bash
ollama --version
```

3. Execute o CLI em modo verboso para capturar contexto:

```bash
python merlin_cli.py
```

4. Para problemas Linux Agent, valide socket e serviço:

```bash
ls -l /run/linux-agent/agent.sock
systemctl status linux-agent.socket
```

## Quando abrir issue

Abra uma issue se o erro persistir, incluindo comando executado, trecho de log e ambiente utilizado.
