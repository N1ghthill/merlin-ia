# Primeira Invocação do Merlin

Este guia cobre a primeira execução do Merlin no CLI.

## Passo a passo

1. Ative o ambiente:

```bash
source .venv/bin/activate
```

2. Abra o Merlin:

```bash
merlin-ia
```

3. Liste os caminhos ativos:

```text
/paths
```

4. Faça um teste simples:

```text
/help
```

5. Opcionalmente, valide o Linux Agent em modo seguro:

```text
/linux-diagnose ssh 50
```

## Resultado esperado

- Inicialização sem erro fatal.
- Resposta de `/help`.
- Caminhos de dados e histórico visíveis em `/paths`.
