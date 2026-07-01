# Definição das Skills — `novatech-assistant`

Cada skill abaixo segue o mesmo formato: **Nome**, **Descrição** (frase-ativação), **Quem cria**, **Quem consome** e **Frequência**.

---

## Foundation

### `typescript-conventions`
- **Descrição:** Use sempre que for escrever ou revisar código TypeScript no repositório: nomenclatura, `strict: true`, padrão de imports/exports e organização de arquivo.
- **Quem cria:** Tech Lead (validado pelo Dev Sênior)
- **Quem consome:** Todos os Devs (Pleno e Sênior) + agente de codificação (Copilot/Claude Code) em qualquer geração de código
- **Frequência:** Alta

### `error-handling`
- **Descrição:** Use sempre que for lançar, capturar ou propagar um erro: uso das custom errors de `shared/errors.ts`, mapeamento erro → status HTTP, formato de mensagem para o usuário final.
- **Quem cria:** Dev Sênior (aprovado pelo Tech Lead)
- **Quem consome:** Devs (Pleno/Sênior) + agente de codificação ao implementar handlers, services e pipeline
- **Frequência:** Alta

### `logging-padrao`
- **Descrição:** Use sempre que for instrumentar logs em uma function, service ou pipeline: níveis do pino, campos obrigatórios (`requestId`, `module`, `duration`) e o que nunca deve ser logado (PII, prompt completo, chunks completos).
- **Quem cria:** Dev Sênior
- **Quem consome:** Devs + agente de codificação ao instrumentar qualquer módulo novo
- **Frequência:** Alta

### `configuracao-de-ambiente`
- **Descrição:** Use sempre que for adicionar variável de ambiente, secret ou setting de Azure Function App: onde declarar, como validar no boot (`shared/config.ts`) e convenção de nome por ambiente (dev/staging/prod).
- **Quem cria:** Tech Lead
- **Quem consome:** Devs + pipeline de CD (agente de deploy) + agente de codificação
- **Frequência:** Média

### `project-structure`
- **Descrição:** Use sempre que for decidir onde um arquivo novo deve viver no repositório: mapa artefato → pasta (endpoint, teste, skill, spec, ADR, infra).
- **Quem cria:** Tech Lead
- **Quem consome:** Todos os papéis + qualquer agente ao criar arquivo novo
- **Frequência:** Alta

---

## Domain

### `azure-functions-endpoint`
- **Descrição:** Use sempre que for criar ou alterar um Azure Function HTTP trigger: estrutura `handler → validator → response-builder`, contrato de entrada/saída, padrão de status codes.
- **Quem cria:** Tech Lead + Dev Sênior
- **Quem consome:** Devs (Pleno/Sênior) + agente de codificação em todo endpoint novo (query, feedback, health e futuros)
- **Frequência:** Alta

### `azure-ai-search-integration`
- **Descrição:** Use sempre que for consultar ou indexar no Azure AI Search: padrão de query, filtro por metadado de vigência, paginação e tratamento de score de relevância.
- **Quem cria:** Dev Sênior
- **Quem consome:** Devs + agente de codificação em `services/search.ts` e `pipeline/indexer.ts`
- **Frequência:** Média

### `react-components`
- **Descrição:** Use sempre que for criar um componente React para o painel web: estrutura `components/pages`, props tipadas, convenção de estado local vs. compartilhado.
- **Quem cria:** Dev Pleno (revisado pelo Tech Lead)
- **Quem consome:** Dev Pleno + agente de codificação ao construir o painel web
- **Frequência:** Média

### `testing-patterns`
- **Descrição:** Use sempre que for escrever um teste: quando usar `unit` vs. `integration` vs. `e2e`, uso de `msw` para mocks, convenção de fixtures compartilhadas (`tests/fixtures`).
- **Quem cria:** QA (com apoio do Dev Sênior)
- **Quem consome:** Devs + QA + agente de geração de testes
- **Frequência:** Alta

### `documentacao-tecnica-de-modulo`
- **Descrição:** Use sempre que um módulo/endpoint estiver pronto e precisar de documentação: critério para abrir ADR vs. atualizar README, nível de detalhe esperado em cada um.
- **Quem cria:** Tech Lead
- **Quem consome:** Dev Sênior + Tech Lead + agente de documentação
- **Frequência:** Média

### `especificacao-sdd`
- **Descrição:** Use sempre que for escrever `requirements.md`, `plan.md` ou `tasks.md` de um módulo: papel responsável por cada artefato, ordem de aprovação, nível de atomicidade esperado em `tasks.md`.
- **Quem cria:** Tech Lead
- **Quem consome:** Product Specialist (requirements) + Tech Lead (plan) + Dev com agente de geração de tasks
- **Frequência:** Alta no início do projeto / Média depois

---

## Artifact

### `criar-endpoint-rag`
- **Descrição:** Use sempre que precisar gerar um novo endpoint Azure Function no padrão RAG do projeto: recebe query, busca chunks no Azure AI Search, monta prompt com metadado de vigência, chama Azure OpenAI, retorna resposta com atribuição de fonte.
- **Quem cria:** Dev Sênior (aprovado pelo Tech Lead)
- **Quem consome:** Dev Pleno/Sênior + agente de codificação a cada novo endpoint RAG
- **Frequência:** Alta

### `criar-teste-integracao-endpoint`
- **Descrição:** Use sempre que um endpoint novo/alterado precisar de teste de integração: mocks com `msw` para Azure AI Search e Azure OpenAI, teste de contrato request/response e de casos de erro.
- **Quem cria:** QA (com apoio do Dev que implementou o endpoint)
- **Quem consome:** Devs + QA + agente de geração de testes, disparado logo após `criar-endpoint-rag`
- **Frequência:** Alta

### `criar-card-resposta-react`
- **Descrição:** Use sempre que for gerar o componente React que exibe a resposta do assistente: corpo da resposta, indicação de fonte/documento citado, estados de carregamento e erro.
- **Quem cria:** Dev Pleno
- **Quem consome:** Dev Pleno + agente de codificação ao evoluir o painel web
- **Frequência:** Média

### `criar-formulario-feedback-react`
- **Descrição:** Use sempre que for gerar o formulário de feedback (👍/👎 + comentário) vinculado a uma resposta: validação de campos, estado de envio, chamada ao endpoint `feedback`.
- **Quem cria:** Dev Pleno
- **Quem consome:** Dev Pleno + agente de codificação ao evoluir o painel web
- **Frequência:** Baixa/Média

### `criar-documentacao-de-endpoint`
- **Descrição:** Use sempre que um endpoint for concluído: gera o ADR (se houver decisão arquitetural relevante) e/ou atualiza o README do módulo com contrato, dependências e exemplos de request/response.
- **Quem cria:** Dev Sênior (ADR aprovado pelo Tech Lead)
- **Quem consome:** Tech Lead + novos membros do time (onboarding) + agente de documentação
- **Frequência:** Média

### `criar-spec-produto-sdd`
- **Descrição:** Use sempre que um novo módulo precisar de `requirements.md`: traduz necessidade de negócio da NovaTech em requisitos testáveis, seguindo o template SDD do projeto.
- **Quem cria:** Product Specialist (aprovado pelo Tech Lead)
- **Quem consome:** Tech Lead (para escrever `plan.md`) + Dev com agente de geração de tasks (para `tasks.md`)
- **Frequência:** Média (Alta nos primeiros 5 módulos)
