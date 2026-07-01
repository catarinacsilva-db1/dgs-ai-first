# Árvore de Skills — `novatech-assistant`

> Proposta de estruturação da pasta `skills/` (Anexo C) seguindo a hierarquia **Foundation → Domain → Artifact**. Refina os arquivos já previstos (`typescript-conventions.md`, `error-handling.md`, `azure-functions-endpoint.md` etc.) e adiciona os que faltam para cobrir os 5 artefatos recorrentes do projeto (endpoint RAG, teste de integração, componentes React, documentação de endpoint, spec de produto).

---

## 1) Visão geral da árvore

```
skills/
├── foundation/
│   ├── typescript-conventions.md
│   ├── error-handling.md
│   ├── logging-padrao.md                  (novo)
│   ├── configuracao-de-ambiente.md        (novo)
│   └── project-structure.md
│
├── domain/
│   ├── azure-functions-endpoint.md
│   ├── azure-ai-search-integration.md
│   ├── react-components.md
│   ├── testing-patterns.md
│   ├── documentacao-tecnica-de-modulo.md  (novo)
│   └── especificacao-sdd.md               (novo)
│
└── artifact/
    ├── criar-endpoint-rag.md
    ├── criar-teste-integracao-endpoint.md
    ├── criar-card-resposta-react.md       (novo — separa card de resposta)
    ├── criar-formulario-feedback-react.md (novo — separa form de feedback)
    ├── criar-documentacao-de-endpoint.md  (novo)
    └── criar-spec-produto-sdd.md          (novo)
```

**Racional da divisão:**
- Os itens do Anexo C que já existiam foram mantidos com o mesmo nome sempre que possível.
- "Componentes React (cards de resposta, formulários de feedback)" foi desdobrado em **duas** skills Artifact porque são receitas de geração diferentes (renderização read-only vs. formulário com validação/estado de envio), evitando uma skill genérica demais.
- "Documentação técnica de endpoints" e "Specs de produto" não tinham Domain correspondente no Anexo C original — foram criadas duas skills Domain novas (`documentacao-tecnica-de-modulo`, `especificacao-sdd`) para sustentar os Artifacts respectivos, mantendo a regra de que todo Artifact precisa de um Domain por trás.

---

## 2) Tabela Foundation

| Skill | Descrição (frase-ativação) | Quem cria | Quem consome (papel + agentes) | Frequência | Dependências |
|---|---|---|---|---|---|
| `typescript-conventions` | Use sempre que for escrever ou revisar código TypeScript no repositório: nomenclatura, `strict: true`, padrão de imports/exports e organização de arquivo. | Tech Lead (validado pelo Dev Sênior) | Todos os Devs + agente de codificação (Copilot/Claude Code) em qualquer geração de código | Alta | — |
| `error-handling` | Use sempre que for lançar, capturar ou propagar um erro: uso das custom errors de `shared/errors.ts`, mapeamento erro→status HTTP, formato de mensagem para o usuário final. | Dev Sênior (aprovado pelo Tech Lead) | Devs (Pleno/Sênior) + agente de codificação ao implementar handlers/services/pipeline | Alta | — |
| `logging-padrao` | Use sempre que for instrumentar logs em uma function, service ou pipeline: níveis do pino, campos obrigatórios (`requestId`, `module`, `duration`) e o que nunca deve ser logado (PII, prompt completo, chunks completos). | Dev Sênior | Devs + agente de codificação ao instrumentar qualquer módulo novo | Alta | — |
| `configuracao-de-ambiente` | Use sempre que for adicionar variável de ambiente, secret ou setting de Azure Function App: onde declarar, como validar no boot (`shared/config.ts`) e convenção de nome por ambiente (dev/staging/prod). | Tech Lead | Devs + pipeline de CD (agente de deploy) + agente de codificação | Média | — |
| `project-structure` | Use sempre que for decidir onde um arquivo novo deve viver no repositório: mapa artefato→pasta (endpoint, teste, skill, spec, ADR, infra). | Tech Lead | Todos os papéis + qualquer agente ao criar arquivo novo | Alta | — |

---

## 3) Tabela Domain

| Skill | Descrição (frase-ativação) | Quem cria | Quem consome (papel + agentes) | Frequência | Dependências (Foundation) |
|---|---|---|---|---|---|
| `azure-functions-endpoint` | Use sempre que for criar/alterar um Azure Function HTTP trigger: estrutura `handler → validator → response-builder`, contrato de entrada/saída, padrão de status codes. | Tech Lead + Dev Sênior | Devs (Pleno/Sênior) + agente de codificação em todo endpoint novo (query, feedback, health e futuros) | Alta | `typescript-conventions`, `error-handling`, `logging-padrao`, `configuracao-de-ambiente`, `project-structure` |
| `azure-ai-search-integration` | Use sempre que for consultar ou indexar no Azure AI Search: padrão de query, filtro por metadado de vigência, paginação e tratamento de score de relevância. | Dev Sênior | Devs + agente de codificação em `services/search.ts` e `pipeline/indexer.ts` | Média | `typescript-conventions`, `error-handling`, `logging-padrao`, `configuracao-de-ambiente` |
| `react-components` | Use sempre que for criar um componente React para o painel web: estrutura `components/pages`, props tipadas, convenção de estado local vs. compartilhado. | Dev Pleno (revisado pelo Tech Lead) | Dev Pleno + agente de codificação ao construir o painel web | Média | `typescript-conventions`, `project-structure` |
| `testing-patterns` | Use sempre que for escrever um teste: quando usar `unit` vs. `integration` vs. `e2e`, uso de `msw` para mocks, convenção de fixtures compartilhadas (`tests/fixtures`). | QA (com apoio do Dev Sênior) | Devs + QA + agente de geração de testes | Alta | `typescript-conventions`, `error-handling`, `project-structure` |
| `documentacao-tecnica-de-modulo` | Use sempre que um módulo/endpoint estiver pronto e precisar de documentação: critério para abrir ADR vs. atualizar README, nível de detalhe esperado em cada um. | Tech Lead | Dev Sênior + Tech Lead + agente de documentação | Média | `project-structure` |
| `especificacao-sdd` | Use sempre que for escrever `requirements.md`, `plan.md` ou `tasks.md` de um módulo: papel responsável por artefato, ordem de aprovação, nível de atomicidade esperado em `tasks.md`. | Tech Lead | Product Specialist (requirements) + Tech Lead (plan) + Dev com agente de geração de tasks | Alta no início / Média depois | `project-structure` |

---

## 4) Tabela Artifact

| Skill | Descrição (frase-ativação) | Quem cria | Quem consome (papel + agentes) | Frequência | Dependências (Domain → Foundation) |
|---|---|---|---|---|---|
| `criar-endpoint-rag` | Use sempre que precisar gerar um novo endpoint Azure Function no padrão RAG do projeto: recebe query, busca chunks no Azure AI Search, monta prompt com metadado de vigência, chama Azure OpenAI, retorna resposta com atribuição de fonte. | Dev Sênior (aprovado pelo Tech Lead) | Dev Pleno/Sênior + agente de codificação a cada novo endpoint RAG | Alta | `azure-functions-endpoint`, `azure-ai-search-integration` → `typescript-conventions`, `error-handling`, `logging-padrao`, `configuracao-de-ambiente` |
| `criar-teste-integracao-endpoint` | Use sempre que um endpoint novo/alterado precisar de teste de integração: mocks com `msw` para Azure AI Search e Azure OpenAI, teste de contrato request/response e de casos de erro. | QA (com apoio do Dev que implementou o endpoint) | Devs + QA + agente de geração de testes, disparado logo após `criar-endpoint-rag` | Alta | `testing-patterns`, `azure-functions-endpoint` → `typescript-conventions`, `error-handling` |
| `criar-card-resposta-react` | Use sempre que for gerar o componente React que exibe a resposta do assistente: corpo da resposta, indicação de fonte/documento citado, estados de carregamento e erro. | Dev Pleno | Dev Pleno + agente de codificação ao evoluir o painel web | Média | `react-components` → `typescript-conventions`, `project-structure` |
| `criar-formulario-feedback-react` | Use sempre que for gerar o formulário de feedback (👍/👎 + comentário) vinculado a uma resposta: validação de campos, estado de envio, chamada ao endpoint `feedback`. | Dev Pleno | Dev Pleno + agente de codificação ao evoluir o painel web | Baixa/Média | `react-components` → `typescript-conventions`, `project-structure` |
| `criar-documentacao-de-endpoint` | Use sempre que um endpoint for concluído: gera o ADR (se houver decisão arquitetural relevante) e/ou atualiza o README do módulo com contrato, dependências e exemplos de request/response. | Dev Sênior (ADR aprovado pelo Tech Lead) | Tech Lead + novos membros do time (onboarding) + agente de documentação | Média | `documentacao-tecnica-de-modulo` → `project-structure` |
| `criar-spec-produto-sdd` | Use sempre que um novo módulo precisar de `requirements.md`: traduz necessidade de negócio da NovaTech em requisitos testáveis, seguindo o template SDD do projeto. | Product Specialist (aprovado pelo Tech Lead) | Tech Lead (para escrever `plan.md`) + Dev com agente de geração de tasks (para `tasks.md`) | Média (Alta nos primeiros 5 módulos) | `especificacao-sdd` → `project-structure` |

---

## 5) Mapa de dependências entre skills

```
FOUNDATION
├─ typescript-conventions ───┬─────────────────────────────────────────────┐
├─ error-handling ───────────┼───────────────┬─────────────┐               │
├─ logging-padrao ───────────┼───────────────┤             │               │
├─ configuracao-de-ambiente ─┤               │             │               │
└─ project-structure ────────┴───┬───┬───┬───┴───┬─────┬───┴───┬───────┐  │
                                  │   │   │       │     │       │       │  │
DOMAIN                            ▼   ▼   ▼       ▼     ▼       ▼       ▼  ▼
azure-functions-endpoint ────────●
azure-ai-search-integration ────────●
react-components ────────────────────────●
testing-patterns ─────────────────────────────●
documentacao-tecnica-de-modulo ────────────────────●
especificacao-sdd ───────────────────────────────────────●

ARTIFACT
criar-endpoint-rag              ← azure-functions-endpoint + azure-ai-search-integration
criar-teste-integracao-endpoint ← testing-patterns + azure-functions-endpoint
criar-card-resposta-react       ← react-components
criar-formulario-feedback-react ← react-components
criar-documentacao-de-endpoint  ← documentacao-tecnica-de-modulo
criar-spec-produto-sdd          ← especificacao-sdd
```

**Leitura prática da cadeia:** nenhum Artifact deve ser executado sem o Domain correspondente carregado, e nenhum Domain sem o Foundation correspondente — isso é o que garante que `criar-endpoint-rag`, por exemplo, já "sabe" tratar erro no formato certo, logar no formato certo e ler configuração do jeito certo, sem precisar redefinir isso a cada geração.

---

## 6) Top 5 skills mais críticas para o início do projeto

| # | Skill | Nível | Justificativa |
|---|---|---|---|
| 1 | `project-structure` | Foundation | Toda a árvore de specs/skills/src está com pastas vazias. Sem essa skill definida primeiro, cada pessoa (e cada agente) decide "na mão" onde salvar cada coisa — gerando inconsistência que se propaga para todas as outras skills. |
| 2 | `typescript-conventions` | Foundation | Código começa a ser escrito desde o primeiro endpoint. Sem convenção fixada antes do primeiro PR, o retrabalho de padronização depois é caro (afeta 100% dos arquivos `.ts`). |
| 3 | `especificacao-sdd` | Domain | As 5 pastas em `specs/` estão vazias. Sem esse padrão, `requirements.md`/`plan.md`/`tasks.md` saem com granularidade e formato diferentes entre módulos — o problema que a Catarina já vem resolvendo manualmente ao auditar `tasks.md` por atomicidade. |
| 4 | `azure-functions-endpoint` | Domain | É o Domain do componente mais crítico da arquitetura (API do assistente) e pré-requisito direto do Artifact mais recorrente do projeto (`criar-endpoint-rag`). Sem ele, `query`, `feedback` e `health` nascem com estruturas de handler divergentes. |
| 5 | `criar-endpoint-rag` | Artifact | É o artefato mais repetido ao longo do projeto e o "coração" funcional do assistente. Ter essa receita pronta antes de codificar o `query-endpoint` acelera a primeira entrega real e evita que o padrão RAG seja inventado de novo em cada endpoint subsequente. |
