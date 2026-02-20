# 🤝 Contribuindo para o Merlin IA

## Ambiente de Desenvolvimento

```bash
git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Testes

NUNCA quebre os testes. Mantenha sempre:

```bash
pytest tests/ -v                     # 91 testes devem passar
pytest --cov=merlin_cli tests/       # >70%
pytest --cov=executor tests/          # >60%
```

## Estrutura

- `merlin/` - Core do assistente
- `executor/` - Linux Agent
- `electron/` - UI Desktop
- `tests/` - Testes (mantenha sempre atualizados)

## Pull Requests

1. Faça um fork do projeto
2. Crie uma branch: `git checkout -b feature/amazing`
3. Commit suas mudanças: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing`
5. Abra um Pull Request

## Padrões

- Python: Black + isort
- JavaScript: Prettier
- Testes: pytest obrigatório
- Documentação: atualize sempre
