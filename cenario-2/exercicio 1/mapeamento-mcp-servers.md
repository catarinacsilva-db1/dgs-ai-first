# Mapeamento de MCP Servers — NovaTech Assistant

## Mapeamento de MCP Servers

| MCP Server Proposto | Sistemas Conectados | Tools Expostas | Resources Expostos | Prompts Expostos | Consumidores (papéis/ferramentas) | Disponibilidade (Público / Construir / Validar) | Justificativa |
|---|---|---|---|---|---|---|---|
| **mcp-github** | GitHub (`db1/novatech-assistant`) | `get_file_contents`, `list_files`, `create_pull_request`, `create_issue`, `list_branches`, `get_commit`, `search_code` | Árvore do repositório, conteúdo de arquivos, PRs abertos, histórico de issues | Template de descrição de PR; template de mensagem de commit | Tech Lead (revisão), Dev Pleno e Dev Sênior (Copilot + Claude Code), QA (rastreamento de defeitos) | Validar | Server oficial existia em `modelcontextprotocol/servers` mas foi arquivado upstream — confirmar substituto mantido antes de adotar |
| **mcp-azure-ai-search** | Azure AI Search (índice vetorial de documentos da NovaTech) | `search_documents`, `get_document_by_id`, `list_indexes`, `describe_index_schema` | Schema do índice ativo, chunks recuperados por consulta semântica, contagem de documentos por versão | — | Dev Pleno e Dev Sênior (desenvolvimento e depuração do pipeline RAG), QA (validação de retrieval e cobertura de chunks) | Construir | Não existe server MCP público e estável para Azure AI Search; requer implementação customizada com autenticação via Managed Identity ou chave de API |
| **mcp-azure-openai** | Azure OpenAI (deployment GPT-4o + modelo de embeddings) | `create_completion`, `create_embedding`, `list_deployments`, `get_deployment_config` | Configurações de deployment ativos, limites de tokens por modelo | — | Dev Pleno e Dev Sênior (testes de integração e prompt engineering), QA (rodadas de avaliação automatizada) | Construir | Não há server MCP público para Azure OpenAI especificamente; difere do OpenAI padrão por exigir endpoint próprio + deployment name + autenticação Entra ID |
| **mcp-azure-devops** | Azure DevOps (boards, backlog, sprints) | `list_work_items`, `create_work_item`, `update_work_item_status`, `list_sprints`, `get_board_view`, `query_items_by_iteration` | Backlog do sprint atual, work items por status, membros do time e capacidade | Template de criação de work item (tipo, título, critérios de aceite, estimativa) | Tech Lead (planejamento de sprint), Delivery Manager (acompanhamento), Product Specialist (gestão de backlog) — via Claude Cowork e Claude chat | Validar | Existem implementações de comunidade não oficiais; ausência de server Microsoft-mantido — avaliar maturidade antes de decidir entre reutilizar ou construir |
| **mcp-confluence** | Confluence da NovaTech (documentação de negócio — somente leitura) | `search_pages`, `get_page_content`, `list_spaces`, `get_page_children` | Conteúdo de páginas, estrutura de espaços autorizados (escopo restrito a espaços da NovaTech) | — | Todos os papéis (contexto de negócio para decisões), Claude Code, Claude Cowork | Validar | Atlassian publicou MCP server oficial; validar se versão disponível permite escopo read-only por espaço para impedir que agentes escrevam em documentação da NovaTech |
| **mcp-filesystem** | Repositório local — pastas `./src`, `./specs`, `./skills`, `./docs`, `./data` | `read_file`, `write_file`, `list_directory`, `search_files`, `move_file` | Conteúdo de arquivos de código, specs SDD, skills do projeto, documentação local | — | Dev Pleno e Dev Sênior (Claude Code, Copilot), Tech Lead (revisão de artefatos), QA (leitura de fixtures) | Público | `@modelcontextprotocol/server-filesystem` — server de referência oficial; escopo obrigatoriamente limitado às pastas autorizadas para impedir acesso a segredos e variáveis de ambiente |
| **mcp-git** | Repositório Git local (`db1/novatech-assistant`) | `git_log`, `git_diff`, `git_status`, `git_branch`, `git_show`, `git_blame` | Histórico de commits, diffs entre branches, lista de branches ativas, autoria por arquivo | — | Dev Pleno e Dev Sênior (Claude Code), Tech Lead (análise de histórico e revisão de mudanças) | Público | `mcp-server-git` (via uvx) — server de referência oficial; complementa `mcp-filesystem` com visibilidade de histórico e evolução do código sem duplicar acesso a arquivos |
| **mcp-memory** | Grafo de conhecimento persistente local | `create_entities`, `create_relations`, `search_nodes`, `open_nodes`, `delete_entities` | Glossário de linguagem ubíqua, decisões arquiteturais sintetizadas (ADRs), padrões e anti-padrões registrados entre sessões | — | Todos os papéis via agentes Claude (manutenção de contexto entre sessões de trabalho, onboarding de novos membros) | Público | `@modelcontextprotocol/server-memory` — server de referência oficial; resolve a ausência de memória persistente entre sessões para termos do domínio, decisões e convenções do projeto |

---

## Permissões Mínimas por MCP Server (Least Privilege)

### mcp-github

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Escopo de repositório | Somente `db1/novatech-assistant` | Agentes não devem enxergar outros repositórios da organização DB1 |
| Operações de leitura | `contents:read`, `metadata:read`, `pull_requests:read`, `issues:read` | Necessárias para navegação de código, revisão de PRs e rastreamento de issues |
| Operações de escrita | `pull_requests:write`, `issues:write` | Restrito a criação de PRs e issues — agentes **não** devem fazer push direto em branches |
| Operações bloqueadas | Push direto em `main` e `develop`, merge sem revisão humana, gestão de secrets, configurações do repositório | Evita que um agente comprometa branches protegidas ou exponha variáveis de ambiente |
| Identidade | Token de serviço dedicado (não token pessoal de desenvolvedor) | Garante rastreabilidade das ações do agente separada das ações humanas |

---

### mcp-azure-ai-search

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Role Azure | `Search Index Data Reader` | Suficiente para consultas semânticas e leitura de documentos — não permite criar, modificar ou deletar índices |
| Escopo de índice | Restrito ao índice `novatech-docs` | Agentes não devem enxergar índices de outros projetos na mesma instância Azure AI Search |
| Operações permitidas | `search`, `get` (documento por ID), `suggest` | Conjunto mínimo para o fluxo RAG funcionar |
| Operações bloqueadas | `index` (indexar documentos), `delete` (remover documentos), criação ou deleção de índices | O pipeline de ingestão é processo separado e controlado — agentes de consulta não devem modificar a base |
| Autenticação | Managed Identity da Azure Function (sem chave de API em variável de ambiente) | Elimina o risco de vazamento de chave via código ou logs |

---

### mcp-azure-openai

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Role Azure | `Cognitive Services OpenAI User` | Permite chamadas de completion e embedding — não permite criar deployments, ajustar modelos ou visualizar configurações de cobrança |
| Escopo de deployment | Restrito aos deployments `gpt-4o-novatech` e `text-embedding-novatech` | Agentes não devem acionar deployments de outros projetos ou modelos não homologados |
| Operações permitidas | `completions`, `embeddings` | Conjunto estritamente necessário para o fluxo de geração e indexação |
| Operações bloqueadas | Criação ou deleção de deployments, fine-tuning, acesso a logs de uso, acesso a configurações de billing | Impede que um agente altere configurações de modelo ou acesse dados de consumo |
| Limites de uso | Rate limit por deployment configurado no Azure (ex: 100K TPM) | Protege contra consumo excessivo involuntário por agentes em loop |
| Autenticação | Managed Identity da Azure Function (sem chave de API exposta) | Mesma razão do mcp-azure-ai-search — elimina superfície de vazamento |

---

### mcp-azure-devops

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Escopo de organização | Somente projeto `NovaTech Assistant` dentro da organização DevOps | Agentes não devem enxergar boards ou backlogs de outros projetos da DB1 |
| Operações de leitura | Leitura de work items, sprints, boards e membros do time | Necessárias para acompanhamento e geração de contexto de planejamento |
| Operações de escrita | Criação e atualização de work items (título, descrição, status, estimativa) | Restrito ao necessário para que Tech Lead e Delivery Manager registrem tarefas via agente |
| Operações bloqueadas | Deleção de work items, gestão de pipelines de CI/CD, configurações do projeto, gestão de usuários e permissões | Agentes de planejamento não devem interferir na infraestrutura de entrega |
| Identidade | Service principal dedicado (PAT com escopo mínimo, sem admin) | Rastreabilidade e revogação independente das credenciais humanas |

---

### mcp-confluence

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Tipo de acesso | Somente leitura (`read`) — sem nenhuma permissão de escrita | Documentação da NovaTech é propriedade do cliente; agentes nunca devem modificá-la |
| Escopo de espaços | Restrito aos espaços autorizados da NovaTech (ex: `NOVATECH-DOC`, `NOVATECH-POL`) | Impede que agentes acessem espaços internos da DB1 ou outros clientes hospedados na mesma instância Confluence |
| Operações permitidas | `search_pages`, `get_page_content`, `list_spaces` (somente espaços autorizados), `get_page_children` | Conjunto mínimo para recuperação de contexto de negócio |
| Operações bloqueadas | Criação, edição ou deleção de páginas, comentários, anexos e gerenciamento de permissões | Risco direto de contaminação da documentação oficial do cliente |
| Autenticação | Token de serviço read-only dedicado ao projeto NovaTech Assistant | Evita que a credencial usada por agentes coincida com a de um usuário humano com permissões de edição |

---

### mcp-filesystem

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Pastas permitidas (leitura + escrita) | `./src`, `./specs`, `./skills`, `./docs`, `./prompts`, `./tests` | Escopo mínimo para que agentes de desenvolvimento operem sem acesso a dados sensíveis |
| Pastas permitidas (somente leitura) | `./data/retrieval-corpus` | Corpus de referência do RAG — agentes de consulta leem, mas não modificam |
| Pastas explicitamente bloqueadas | `.env`, `.env.*`, `./infra`, `./node_modules`, `./secrets`, qualquer arquivo `*.key`, `*.pem`, `*.pfx` | Impede exposição de credenciais, chaves e configurações de infraestrutura a agentes locais |
| Operações bloqueadas | Deleção permanente de arquivos, execução de binários | `write_file` e `move_file` são suficientes — agentes não precisam deletar nem executar |
| Configuração de escopo | Pastas declaradas explicitamente no argumento `args` do server (allowlist, não blocklist) | Abordagem allowlist é mais segura: qualquer pasta não listada é inacessível por padrão |

---

### mcp-git

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Modo de acesso | Somente leitura do histórico Git | Agentes usam o server para navegar em commits, diffs e branches — não para escrever |
| Operações permitidas | `git_log`, `git_diff`, `git_status`, `git_show`, `git_branch`, `git_blame` | Conjunto necessário para análise de histórico e revisão de mudanças |
| Operações bloqueadas | `git_commit`, `git_push`, `git_merge`, `git_rebase`, `git_reset`, `git_tag` | Operações de escrita no histórico Git devem ser exclusivamente humanas ou de pipelines CI/CD auditados |
| Escopo de repositório | Somente o repositório local `db1/novatech-assistant` | Server aponta para `--repository .` — não deve ter acesso a repositórios fora do diretório do projeto |

---

### mcp-memory

| Dimensão | Permissão Mínima | Justificativa |
|---|---|---|
| Escopo do grafo | Namespace isolado por projeto (`novatech-assistant`) | Impede que entidades e relações de outros projetos eventualmente ativos contaminem o grafo deste projeto |
| Operações permitidas | `create_entities`, `create_relations`, `search_nodes`, `open_nodes` | Necessárias para manter e consultar glossário, decisões e padrões do projeto |
| Operações restritas | `delete_entities`, `delete_relations` | Permitidas somente para Tech Lead e Dev Sênior — agentes não devem apagar entidades de forma autônoma |
| Tipos de dados permitidos | Termos do domínio, decisões arquiteturais sintetizadas, padrões e anti-padrões | Dados operacionais sensíveis (credenciais, tokens, PII) nunca devem ser armazenados no grafo |
| Persistência | Armazenamento local (arquivo JSON do server-memory) — sem sincronização com serviços externos | Mantém o grafo de conhecimento dentro do perímetro controlado da DB1 |

---

## Observações de validação

- **mcp-github:** O server oficial `modelcontextprotocol/servers/github` foi arquivado upstream — confirmar se existe fork ativo com manutenção contínua ou substituto oficial antes de incluir no `.mcp/mcp.json` de produção.
- **mcp-azure-devops:** As implementações disponíveis são de comunidade sem SLA de manutenção — avaliar cobertura de APIs (especialmente `query_items_by_iteration`), compatibilidade com a versão de Azure DevOps usada pelo time, e maturidade de autenticação antes de decidir entre adotar ou construir internamente.
- **mcp-confluence:** Confirmar se o server oficial Atlassian permite configurar escopo read-only restrito a espaços específicos da NovaTech; sem essa garantia, o server expõe o risco de um agente com permissões mais amplas escrever ou sobrescrever documentação de negócio do cliente.
