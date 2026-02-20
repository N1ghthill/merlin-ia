# Primeira Invocação do Merlin

Este guia cobre a primeira execução do Merlin em modo controlado para validar ambiente, resposta inicial e logs principais.

## Objetivo

Executar o Merlin no CLI com segurança para confirmar que dependências, modelos e integração básica estão funcionais.

## Passo a passo

1. Ative o ambiente virtual:

```bash
source .venv/bin/activate
```

2. Execute o Merlin no CLI:

```bash
python merlin_cli.py
```

3. Faça um comando simples de teste:

```text
/help
```

4. Opcionalmente, teste um comando Linux em modo dry-run:

```text
/linux-diagnose ssh 50
```

## Resultado esperado

- Inicialização sem erro fatal.
- Resposta do comando `/help`.
- Logs sendo gerados normalmente.
