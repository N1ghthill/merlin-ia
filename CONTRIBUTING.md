# Contribuindo para o Merlin IA

## Ambiente de desenvolvimento

```bash
git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia

sudo apt install -y python3 python3-pip python3-venv

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

Se quiser manter histórico, Chroma e scrolls dentro do próprio repositório:

```bash
export MERLIN_STORAGE_MODE=project
```

## Validações locais

```bash
make test
make compile
```

Para rodar cobertura:

```bash
pytest --cov=merlin_cli --cov=merlin --cov=executor tests/
```

## Estrutura

- `merlin_cli.py`: CLI.
- `merlin_api.py`: API local e contrato da futura interface web.
- `rag_indexer.py`: reindexação completa.
- `merlin/`: paths e integrações.
- `executor/`: Linux Agent.
- `tests/`: suíte automatizada.
- `docs/`: documentação de uso e operação.

## Pull requests

1. Crie uma branch.
2. Faça a mudança completa, incluindo testes e docs quando necessário.
3. Rode `make test` e `make compile`.
4. Abra a PR com contexto, impacto e forma de validação.

## Regras práticas

- Mantenha `README.md` e `docs/README.md` alinhados com o estado público do projeto.
- Não quebre a compatibilidade do CLI sem atualizar a documentação.
- Prefira mudanças pequenas e verificáveis.
- Não adicione dependências pesadas sem necessidade real.
- Se uma interface ou script sair de escopo, remova a menção pública no mesmo conjunto de mudanças.
- Se mexer em fluxos do Linux Agent, revise também os docs em `docs/04-*` a `docs/18-*`.
