# 🧙 Merlin IA

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![Tests](https://img.shields.io/github/actions/workflow/status/N1ghthill/merlin-ia/tests.yml?branch=main&label=tests)
![Last Commit](https://img.shields.io/github/last-commit/N1ghthill/merlin-ia)
![Issues](https://img.shields.io/github/issues/N1ghthill/merlin-ia)

**Seu assistente Linux inteligente e 100% privado**
_Automatize tarefas, consulte documentos e gerencie o sistema com IA, tudo offline._

## ✨ Por que usar o Merlin?

Cansado de depender da nuvem para usar IA com seus arquivos? Preocupado com a privacidade dos seus dados? O Merlin IA roda **completamente offline** no seu computador. Use linguagem natural para:

- 📚 **Conversar com seus documentos:** Faça perguntas sobre PDFs, anotações em TXT/MD e obtenha respostas baseadas no conteúdo (RAG).
- 🐧 **Automatizar seu Linux:** Execute diagnósticos, instale pacotes e aplique hardening de segurança com comandos diretos como `/linux-install nginx` ou `/linux-harden ssh`.
- 🖥️ **Escolher sua interface:** Use o **CLI poderoso** para scripts ou a **interface gráfica nativa (Electron)** para interações mais visuais.
- 🔒 **Garantir sua privacidade:** Nenhum dado sai da sua máquina. Tudo processado localmente com Ollama e ChromaDB.

**✅ Perfeito para:** Devs que querem automatizar seu ambiente, times que lidam com dados sensíveis, ou qualquer pessoa que valorize privacidade e produtividade no Linux.

---

## 🚀 Instalação Rápida (Ubuntu/Debian)

```bash
# Baixe o .deb da última release
wget https://github.com/N1ghthill/merlin-ia/releases/latest/download/merlin-ia_0.1.0_amd64.deb

# Instale
sudo dpkg -i merlin-ia_0.1.0_amd64.deb

# Execute
merlin-ia
```

📦 Outros formatos: Windows (`.exe`), macOS (`.dmg`), Linux (`.rpm`) - veja como gerar em [Build do Zero](./docs/build-do-zero.md).

## 📊 Status do Projeto (Robusto e Testado)

| Componente | Status | Cobertura de Testes |
| --- | --- | --- |
| RAG Core | ✅ Estável | 93% |
| Linux Agent | ✅ Robusto | 68% |
| CLI | ✅ Completo | 71% |
| Electron UI | ✅ Nova | - |
| Total | **91 testes** | **Média 77%** |

## 🧠 Como Funciona (Simples e Direto)

1. Adicione seus documentos na pasta `scrolls/`.
2. O Merlin indexa o conteúdo, transformando em embeddings (via Ollama + ChromaDB).
3. Faça uma pergunta na interface gráfica ou no CLI.
4. O Merlin busca os trechos mais relevantes e gera uma resposta contextualizada para você.

## 🐧 Linux Agent: Comandos Mágicos

Digite estes comandos diretamente no chat para controlar seu sistema:

- `/linux-diagnose ssh 50` -> Diagnóstico detalhado do serviço SSH.
- `/linux-install nginx` -> Instala o Nginx (com simulação dry-run primeiro).
- `/linux-harden ssh` -> Aplica configurações de hardening no SSH automaticamente.
- `/linux-lockdown` -> Ativa o modo read-only do sistema para segurança máxima.

## 🛠️ Para Desenvolvedores (Contribua e Adapte)

```bash
git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt requirements-dev.txt

# Rodar testes
pytest tests/ -v

# Gerar pacote .deb
cd electron && npm run dist:deb
```

📚 Documentação completa: [Guia de Instalação](./docs/01-instalacao.md) | [Como Usar](./docs/02-como-usar.md) | [Comandos do Linux Agent](./docs/18-merlin-cli-commands.md) | [API](./docs/api.md) | [Build do Zero](./docs/build-do-zero.md)

## 🤝 Contribuindo

Adoramos contribuições. Seja corrigindo um bug, sugerindo uma feature ou melhorando a documentação. Dá uma olhada no [CONTRIBUTING.md](./CONTRIBUTING.md) para começar.

Se você usou e gostou, deixe uma estrela ⭐ no repositório. Isso ajuda outras pessoas a encontrarem o projeto e nos motiva a continuar.

## 📜 Licença

MIT - Use, modifique e compartilhe livremente.

## 🧙 Feito com magia por N1ghthill
