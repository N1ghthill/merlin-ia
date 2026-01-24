<div align="center">

# 🧙 Merlin IA
**Assistente local com RAG (Retrieval-Augmented Generation)**  
Chat inteligente com sua base de conhecimento: documentos, anotações e arquivos — com respostas contextualizadas.

**Local AI assistant with RAG (Retrieval-Augmented Generation)**  
Chat with your knowledge base: docs, notes and files — with grounded, contextual answers.

<br/>

<!-- Badges -->
![Status](https://img.shields.io/badge/status-active-success)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-informational)

</div>

---

## ✨ O que é | What is it?
O **Merlin IA** é um assistente local que combina **busca inteligente (RAG)** + **respostas naturais**, permitindo conversar com seus próprios conteúdos com mais precisão.

Merlin IA is a local assistant that combines **smart retrieval (RAG)** + **natural language answers**, allowing you to chat with your own files with better accuracy.

---

## 🚀 Principais recursos | Key Features
- 📚 **RAG / busca contextual** em documentos
- 🔎 **Respostas com base no conteúdo** (menos “achismo”, mais contexto)
- 🗂️ Indexação simples de arquivos e pastas
- ⚡ Focado em produtividade: pesquisa, resumo e suporte técnico
- 🧩 Arquitetura extensível (dá pra plugar novos loaders e fontes)

---

## 🧠 Como funciona | How it works
1. Você adiciona documentos (PDF/TXT/MD/etc)  
2. O Merlin indexa e transforma em “memória” (embeddings)  
3. Quando você pergunta algo, ele busca trechos relevantes  
4. O modelo gera a resposta com base nos trechos encontrados

---

## 🖥️ Demo (exemplo) | Demo (example)
**Pergunta / Question**
> “Resuma os pontos mais importantes do meu arquivo de planejamento.”

**Resposta / Answer**
> “Aqui está um resumo baseado no documento X… (com trechos e contexto)”

> 💡 Dica: coloque um GIF aqui depois (fica MUITO forte no GitHub)

---

## 📦 Instalação | Installation

### 1) Clonar o projeto | Clone

git clone https://github.com/N1ghthill/merlin-ia.git
cd merlin-ia

### 2) Criar ambiente | Create venv
python -m venv .venv
source .venv/bin/activate

### 3) Instalar dependências | Install deps
pip install -r requirements.txt

## ▶️ Como usar | Usage

### Ajuste o comando conforme o seu entrypoint (CLI/API).

Rodar o Merlin
python main.py

Indexar documentos (exemplo)
python main.py --ingest ./docs

Fazer uma pergunta
python main.py --ask "Qual é o resumo do arquivo X?"

## ⚙️ Configuração | Configuration

### Crie um .env na raiz:

MODEL_NAME=seu-modelo-aqui
EMBEDDINGS_MODEL=seu-embeddings-aqui
DATA_PATH=./data

## 🗺️ Roadmap

Melhorar ingestão para PDF/Docx/HTML

Interface Web simples (chat UI)

Cache e performance de busca

Citações por fonte (mostrar de onde veio cada trecho)

Docker para rodar “1 comando e pronto”

## 🤝 Contribuindo | Contributing

Pull requests são bem-vindos!
Se quiser sugerir melhorias, abre uma Issue com:

### objetivo

passos pra reproduzir

prints/logs (se possível)

## 📜 Licença | License

MIT — use livremente e contribua se quiser.
