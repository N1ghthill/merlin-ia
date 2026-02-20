# Introdução ao Merlin IA

Este guia apresenta o Merlin IA em poucos minutos para você começar com segurança, produtividade e privacidade local.

## O que você vai aprender

- Qual problema o Merlin resolve.
- Como iniciar o assistente no modo CLI e no modo gráfico.
- Como fazer a primeira consulta com base em documentos locais.

## Passo a passo rápido

1. Prepare o ambiente Python:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

2. Garanta que o Ollama esteja disponível localmente:

```bash
ollama --version
```

3. Inicie o Merlin no terminal:

```bash
python merlin_cli.py
```

4. Faça uma primeira pergunta baseada em documentos da pasta `scrolls/`.

## Próximos guias recomendados

- [Instalação](./01-instalacao.md)
- [Como Usar](./02-como-usar.md)
- [Comandos do CLI](./18-merlin-cli-commands.md)
