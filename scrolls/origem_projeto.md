# Origem do Projeto — Merlin IA

## Autor / Desenvolvedor
**Irving Ruas**  
Desenvolvedor Full Stack • Analista de Dados • Gestor de Tráfego  

- Email: irving@ruas.dev.br  
- Site: https://ruas.dev.br  
- GitHub: https://github.com/  
- LinkedIn: https://www.linkedin.com/in/irvingruas/  
- Instagram: https://www.instagram.com/

---

## Visão Geral

O **Merlin IA** é um assistente de inteligência artificial local-first, criado para operar de forma privada, autônoma e totalmente controlada pelo desenvolvedor.

O projeto nasce da necessidade prática de:
- um assistente confiável,
- com memória persistente,
- capaz de evoluir com o usuário,
- sem dependência de serviços cloud públicos,
- com controle total sobre código, dados e infraestrutura.

**Princípio central do projeto:** 
> *Primeiro funcionar. Depois ficar bonito.*

---

## Objetivo do Projeto

Construir um assistente pessoal de IA que:

- rode localmente (CPU/GPU conforme disponível),
- utilize RAG (Retrieval-Augmented Generation),
- mantenha memória pessoal estruturada,
- consulte documentos locais (“pergaminhos”),
- preserve histórico versionado,
- possa ser expandido futuramente para API, Web ou Service.

---

## Princípios Norteadores

### Técnicos
- Local-first
- Privacidade total
- Simplicidade arquitetural
- Estado explícito e versionado
- Falhas visíveis e controláveis

### Produto
- MVP funcional antes de UI
- Evolução incremental
- Decisões guiadas por uso real
- Automação apenas quando necessária

---

## Arquitetura Atual

### Interface
- CLI (terminal)
- Streaming de respostas
- Interação direta com o modelo local

### Modelo de Linguagem
- Ollama
- Modelo: `qwen2.5:7b`
- Execução local

### Memória

#### Histórico Conversacional
- Persistido em `data/history.jsonl`
- Indexado incrementalmente no ChromaDB
- Utilizado como contexto no RAG

#### Perfil Canônico do Usuário
Arquivo:

