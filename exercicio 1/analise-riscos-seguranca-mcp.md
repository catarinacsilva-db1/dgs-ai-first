# Análise de Riscos de Segurança MCP — NovaTech Assistant

## 1) Risco
Credenciais em variáveis de ambiente com escopo amplo e potencial de exposição em logs/processos (principalmente mcp-github, mcp-azure-openai, mcp-azure-ai-search, mcp-azure-devops, mcp-confluence).

## 2) Impacto
Comprometimento de token pode permitir leitura/escrita indevida em repositório, boards, índices e páginas, além de exfiltração de dados e ações não autorizadas em nome do serviço.

## 3) Mitigação recomendada
- Priorizar autenticação federada/identidade gerenciada (Managed Identity/Entra ID) para Azure Search e Azure OpenAI, removendo chaves estáticas.
- Para GitHub, DevOps e Confluence, usar tokens de serviço dedicados, curta duração e rotação automática.
- Impor política de mascaramento de segredos em logs do host MCP e bloquear dump de env em erros.
- Separar credenciais por server e por ambiente (dev/hml/prd), sem reutilização entre integrações.

## 4) Prioridade
Alta

---

## 1) Risco
Escopo/permissões acima do mínimo no mcp-filesystem e mcp-github (write excessivo ou allowlist incompleta), permitindo acesso além do projeto NovaTech Assistant.

## 2) Impacto
Leitura de arquivos sensíveis locais (por exemplo .env, chaves, infra) e alterações indevidas em branches protegidas/PRs, com risco de vazamento de segredos e regressões de código.

## 3) Mitigação recomendada
- No mcp-filesystem, manter allowlist estrita apenas em pastas necessárias e enforcement real de bloqueio para .env, secrets, infra, chaves e certificados.
- Executar server em usuário/container isolado com ACL de sistema operacional, para que o bloqueio não dependa só de configuração lógica.
- No mcp-github, negar push direto e ações administrativas; manter apenas leitura + criação de PR/issue quando estritamente necessário.
- Aplicar branch protection obrigatória (main/develop) com revisão humana e checks antes de merge.

## 4) Prioridade
Alta

---

## 1) Risco
Servers em status validar/construir (mcp-github, mcp-azure-devops, mcp-confluence, mcp-azure-ai-search, mcp-azure-openai) sendo habilitados sem validação de maturidade, controles de autorização e testes de segurança.

## 2) Impacto
Adoção de implementação instável ou com comportamento inesperado pode abrir superfícies para escrita indevida, bypass de escopo e acesso não autorizado a dados corporativos/cliente.

## 3) Mitigação recomendada
- Manter enabled=false por padrão até passar um gate de segurança formal.
- Criar checklist de entrada em produção: revisão de código do server, teste de autorização negativa, teste de isolamento de escopo, validação de logs sem segredos e teste de abuso de tools.
- Exigir aprovação conjunta de Segurança + Tech Lead para alterar enabled para true.

## 4) Prioridade
Média

---

## 1) Risco
Persistência de conhecimento no mcp-memory sem governança de conteúdo e sem política forte de namespace por projeto/ambiente.

## 2) Impacto
Contaminação de contexto entre projetos e retenção de dados sensíveis (tokens, PII, detalhes internos), com risco de vazamento em respostas futuras e decisões incorretas por contexto misturado.

## 3) Mitigação recomendada
- Namespace obrigatório por projeto e por ambiente (ex.: novatech-assistant-prod separado de dev).
- Bloquear gravação de padrões sensíveis (segredos, PII) por validação no ponto de escrita.
- Definir política de retenção, revisão periódica e limpeza controlada por papel autorizado.
- Auditar operações create/search/open com trilha de auditoria mínima.

## 4) Prioridade
Média

---

## 1) Risco
Permissões de escrita em mcp-azure-devops e mcp-confluence com fronteira funcional pouco rígida (work items/páginas/comentários) e risco de abuso por automação.

## 2) Impacto
Alteração indevida de backlog, status e documentação oficial do cliente, gerando impacto operacional, perda de rastreabilidade e risco contratual.

## 3) Mitigação recomendada
- Confluence em leitura estrita por espaço autorizado; escrita desabilitada no server e no provedor de identidade.
- Azure DevOps com escopo somente no projeto NovaTech Assistant e sem permissão administrativa/pipeline/users.
- Implementar policy-as-code para operações permitidas por server e bloquear por padrão qualquer operação não listada.

## 4) Prioridade
Média
