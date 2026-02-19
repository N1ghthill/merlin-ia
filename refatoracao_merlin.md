**Prompt para Codex (Refatoração Controlada do Merlin)**

**Contexto:** Você é um engenheiro de software especializado em sistemas críticos e agentes autônomos. Você vai auxiliar no refinamento do projeto "Merlin IA", um assistente local com um agente Linux integrado de altíssimo privilégio. **Sua premissa principal é: O PODER DO MERLIN NÃO PODE SER REDUZIDO.** O objetivo é adicionar **camadas de autorização explícita e protocolos de segurança** que tornem seu uso por um usuário avançado (o "Mestre") seguro, sem limitar suas capacidades.

**Arquitetura Atual (Pontos-Chave):**
1.  **Agente Linux:** Integrado via comandos `/linux-*` no `merlin_cli.py`. Ele executa ações reais no sistema (install, harden, exec).
2.  **Executor:** Provavelmente um serviço separado (em `executor/`) que recebe comandos do CLI e os executa com altos privilégios.
3.  **Ações Pendentes:** Usa `data/linux_pending.json` para armazenar ações que requerem confirmação explícita (`/linux-exec CONFIRM EXECUTE <id>`).
4.  **Segurança Atual:** Já possui um conceito de confirmação e uma flag `LINUX_READ_ONLY=1`.

**Problema Específico a Resolver (Modo de Operação e Permissões):**
O Merlin foi projetado para operar com privilégios máximos (root), mas sua execução ideal deveria ser: `[Soquete Systemd] -> [Ativar venv] -> [Executar Merlin]`. Há uma inconsistência na permissão de dois scripts de verificação pós-deploy (`scripts/post_deploy_check.sh` e `scripts/check_requirements.sh`) quando executados fora do contexto do serviço systemd (por exemplo, pelo meu usuário normal). Suspeito que seja um problema de:
*   Contexto de `PATH` entre o usuário do serviço e meu usuário.
*   Propriedade e permissões de arquivos/diretórios criados pelo serviço (como logs ou soquetes).
*   Dependência de variáveis de ambiente que só existem no contexto do serviço.

**Tarefa Específica (Modificação Controlada):**
1.  **Diagnosticar e Corrigir o Problema de Permissão/Path:**
    *   Analise os scripts `scripts/post_deploy_check.sh` e `scripts/check_requirements.sh`. Identifique quais comandos ou caminhos de arquivo eles usam.
    *   Sugira modificações para que esses scripts sejam resilientes ao contexto de execução. Exemplo: usar caminhos absolutos, verificar a existência de comandos antes de usá-los (`command -v`), e não depender de variáveis de ambiente que só existem no serviço.
    *   Proponha uma solução para a propriedade de arquivos. Por exemplo: o serviço systemd deve criar arquivos com permissões que permitam a leitura/escrita pelo grupo do usuário administrador (talvez usando `sg` ou configurando `umask` adequadamente no serviço).

2.  **Reforçar Protocolo de Ações Sensíveis (SEM REDUZIR PODER):**
    *   Revise o fluxo de confirmação de ações (`/linux-exec CONFIRM EXECUTE`). Ele é seguro o bastante? Uma ação confirmada ainda pode ser perigosa, mas é uma decisão consciente do operador.
    *   Implemente um **"Modo de Auditoria Obrigatório"**: Para qualquer ação que modifique o sistema (install, harden, exec), o Merlin DEVE, além da confirmação, logar num arquivo imutável (ex: `/var/log/merlin/audit.log`) o comando exato, o usuário que confirmou (via `whoami`), o timestamp e o ID da requisição. Isso é para rastreabilidade, não para limitar.
    *   Crie um comando `/linux-audit [N]` que mostre os últimos N logs de auditoria.

3.  **Isolamento Inteligente (Módulo Opcional e "Chave Física"):**
    *   Refatore o carregamento dos comandos `/linux-*` no `merlin_cli.py` para que só sejam adicionados ao interpretador SE a variável de ambiente `MERLIN_ENABLE_EXECUTOR=1` estiver setada. Isso é uma **chave física** no ambiente. Por padrão, ela deve estar desligada (ou comentada) no `.env.example`.
    *   Crie um comando de emergência `/linux-lockdown` que: (a) Revoga todas as permissões pendentes (limpa `data/linux_pending.json`), (b) Ativa forçadamente o modo `LINUX_READ_ONLY=1` (sobrescrevendo qualquer configuração), e (c) Mata qualquer processo filho do executor pendente. Esse comando deve ser de fácil acesso.

**Restrições e Instruções Críticas (LEIA COM ATENÇÃO):**
1.  **NÃO** remova ou limite nenhuma capacidade existente do agente Linux. O Merlin deve continuar podendo instalar pacotes, aplicar hardening e executar comandos arbitrários. A segurança virá da **explicitação da autorização e da auditoria**, não da castração.
2.  **NÃO** mude a arquitetra fundamental de comunicação entre o CLI e o executor a menos que seja estritamente necessário para resolver o problema de permissão.
3.  **NÃO** introduza dependências externas pesadas ou mude o modelo de "local-first".
4.  **NÃO** tente "proteger" o sistema contra o usuário root. O usuário do Merlin (eu) sou eu, e eu confio em mim mesmo. O objetivo é evitar que um prompt malicioso ou uma alucinação do modelo cause danos sem uma confirmação explícita e auditada.
5.  **Priorize a clareza e a documentação.** Qualquer solução proposta deve ser acompanhada de comentários no código e, se necessário, uma atualização na documentação relevante (`docs/`).

**Formato da Resposta Esperada:**
Forneça um plano de ação passo-a-passo, com os trechos de código modificados ou novos scripts. Explique o raciocínio por trás de cada mudança, especialmente como ela resolve o problema de permissão sem diminuir o poder do agente.

---
