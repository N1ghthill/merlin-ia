# Ambiente de Referência

Este documento registra um perfil de ambiente usado durante validações do Merlin IA e traz um checklist para reproduzir a configuração.

## Perfil de hardware observado

### CPU

- Cores físicos: 14
- Threads lógicos: 28
- Ollama threads: 14
- Batch size: 256
- Context: 4096
- GPU: AMD RX 550 (sem ROCm)
- Modo: CPU-only otimizado

## Passo a passo para validar o ambiente

1. Verifique versão do Python:

```bash
python3 --version
```

2. Verifique disponibilidade do Ollama:

```bash
ollama --version
```

3. Verifique Node.js e npm para a interface Electron:

```bash
node --version
npm --version
```

4. Execute um teste básico para confirmar o setup:

```bash
pytest tests/ -q
```
