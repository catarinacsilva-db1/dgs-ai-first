# SKILL: project-structure

## Contexto
Esta skill existe para garantir previsibilidade estrutural em um projeto TypeScript modular com Azure Functions no backend e React no frontend.  
Sem um padrão único de estrutura, o time tende a criar pastas e arquivos por conveniência local, gerando acoplamento, duplicidade, imports frágeis, testes difíceis de localizar e alto custo de manutenção.

Problema que esta skill resolve:
- Reduz divergência entre módulos.
- Evita mistura de responsabilidades entre camadas.
- Acelera onboarding, code review e automação por agentes de IA.
- Cria base única para as demais skills (endpoint, testes, docs, specs, prompts).

## Escopo
### O que cobre
- Organização mandatória de pastas e arquivos.
- Convenções de nomenclatura.
- Separação de responsabilidades por camada.
- Localização de testes.
- Localização de specs, prompts e documentação.
- Padrões de import/export.
- Critérios para criação de novos módulos.

### O que não cobre
- Regras detalhadas de lógica de negócio específica de domínio.
- Estratégias avançadas de testes (isso pertence à skill de testing-patterns).
- Políticas de segurança e segredos em profundidade (tratadas por skill específica).
- Decisão de arquitetura macro (tratada via ADR e governança técnica).

### Públicos consumidores
- Desenvolvedores (Pleno/Sênior): implementação e refatoração.
- Tech Lead: definição e aprovação de estrutura.
- QA: navegação e rastreabilidade de testes.
- Product Specialist e Delivery Manager: entendimento de artefatos de specs/docs.
- Agentes de IA: geração consistente de código, testes e documentação.

---

## Regras Prescritivas

### 1) Organização de pastas e arquivos
1. O código de runtime deve ficar apenas sob src.
Justificativa: separa código executável de artefatos de suporte.

2. Cada módulo funcional de backend deve residir em src/functions/<nome-do-modulo>.
Justificativa: facilita ownership e evolução por endpoint.

3. Serviços compartilhados de backend devem residir em src/services.
Justificativa: evita duplicação de integração com dependências externas.

4. Utilitários transversais (retry, config, helpers puros) devem residir em src/shared.
Justificativa: centraliza capacidades reutilizáveis sem acoplar domínio.

5. Frontend React deve residir em src/web/src, com segregação mínima entre pages e components.
Justificativa: separa composição de tela de blocos reutilizáveis.

6. Artefatos não executáveis devem respeitar:
- docs para documentação técnica e operacional.
- prompts para prompts e avaliações.
- specs para requirements/plan/tasks.
Justificativa: evita misturar código com documentação/processo.

7. Não deve haver arquivos soltos na raiz do repositório além dos arquivos de configuração do projeto.
Justificativa: mantém raiz limpa e legível.

### 2) Convenções de nomenclatura
1. Pastas devem usar kebab-case.
Justificativa: padrão estável em sistemas de arquivos e URLs.

2. Arquivos TypeScript devem usar kebab-case e sufixo por papel quando aplicável:
- handler.ts
- validator.ts
- response-builder.ts
Justificativa: nome explicita responsabilidade.

3. Componentes React devem usar PascalCase no nome do componente e arquivo .tsx correspondente.
Justificativa: convenção consolidada do ecossistema React.

4. Testes devem terminar com .test.ts ou .test.tsx.
Justificativa: descoberta automática por runners e consistência de busca.

5. Não deve usar nomes genéricos como utils.ts, helper.ts, service.ts em nível de módulo.
Justificativa: nomes genéricos escondem intenção e aumentam ambiguidade.

### 3) Separação de responsabilidades por camada
1. Handler de Azure Function deve orquestrar fluxo HTTP (entrada, chamada de camadas, saída), sem lógica de negócio pesada.
Justificativa: mantém endpoint simples e testável.

2. Validator deve conter validação de contrato de entrada/saída, sem chamadas externas.
Justificativa: validação deve ser determinística e rápida.

3. Response builder deve padronizar formato de resposta HTTP e mapeamento de erros.
Justificativa: consistência de contrato para clientes.

4. Service deve concentrar integração externa e regras de aplicação relacionadas ao caso de uso.
Justificativa: encapsula dependências e reduz acoplamento no handler.

5. Shared não deve depender de modules específicos de functions.
Justificativa: evita dependência circular e inversão indevida.

### 4) Localização de testes
1. Testes unitários devem ficar em tests/unit.
Justificativa: isolamento de testes de comportamento interno.

2. Testes de integração devem ficar em tests/integration.
Justificativa: valida contrato entre componentes reais/mocados.

3. Testes end-to-end devem ficar em tests/e2e.
Justificativa: separa fluxo ponta a ponta dos demais níveis.

4. Não deve criar arquivos de teste dentro de src (salvo decisão explícita de exceção).
Justificativa: evita poluição do código de produção.

5. Estrutura de testes deve espelhar o módulo alvo sempre que possível.
Justificativa: melhora rastreabilidade e manutenção.

### 5) Localização de specs, prompts e docs
1. Specs de produto/execução devem estar em specs/<modulo>/{requirements.md,plan.md,tasks.md}.
Justificativa: padroniza fluxo de planejamento e execução.

2. Documentação técnica e runbooks devem estar em docs e docs/runbooks.
Justificativa: facilita operação e onboarding.

3. Prompts e evidências de avaliação devem estar em prompts e prompts/eval/eval-results.
Justificativa: rastreabilidade de engenharia assistida por IA.

4. Não deve armazenar specs/prompts/docs dentro de src.
Justificativa: separa artefatos de processo do runtime.

### 6) Padrões de import/export
1. Deve preferir importações por caminho absoluto baseado em alias de projeto (quando configurado), evitando cadeias longas de ../../..
Justificativa: melhora legibilidade e reduz fragilidade em refatorações.

2. Cada arquivo deve exportar apenas o necessário; evitar export default em backend.
Justificativa: favorece contratos explícitos e refatoração segura.

3. Deve haver barrel file (index.ts) apenas quando agregar API pública de módulo; não usar barrel para mascarar dependências internas.
Justificativa: barrel mal usado cria acoplamento implícito.

4. Não deve importar diretamente arquivos internos de outro módulo quando houver ponto de entrada público.
Justificativa: preserva encapsulamento.

5. Frontend React deve separar imports de libs externas, internos absolutos e relativos locais.
Justificativa: padroniza leitura e diffs.

### 7) Critérios para criação de novos módulos
1. Um novo módulo deve ser criado quando houver novo caso de uso com contrato próprio de entrada/saída.
Justificativa: modularidade orientada a comportamento, não por conveniência.

2. Antes de criar módulo, deve verificar reuso em services/shared existentes.
Justificativa: evita duplicidade.

3. Novo módulo deve nascer com:
- estrutura mínima de runtime (handler/validator/response-builder quando aplicável),
- testes mínimos (unit + integration),
- documentação mínima (README de módulo ou seção em docs),
- spec correspondente (requirements/plan/tasks) quando for entrega planejada.
Justificativa: garante completude desde o início.

4. Não deve criar módulo sem owner técnico definido no PR.
Justificativa: evita código órfão.

---

## Exemplos DO/DON'T

### A) Árvore de diretórios (backend + frontend + artefatos)

DO
~~~text
src/
  functions/
    query/
      handler.ts
      validator.ts
      response-builder.ts
  services/
    search.ts
    completion.ts
    prompt-builder.ts
  shared/
    retry.ts
  web/
    src/
      pages/
        ChatPage.tsx
      components/
        ResponseCard.tsx

tests/
  unit/
    query/
      validator.test.ts
  integration/
    query/
      handler.test.ts
  e2e/
    chat-flow.test.ts

docs/
  runbooks/
    query-endpoint.md

prompts/
  eval/
    eval-results/

specs/
  query-endpoint/
    requirements.md
    plan.md
    tasks.md
~~~

DON'T
~~~text
src/
  queryHandler.ts
  utils.ts
  tests/
    query.test.ts
  docs/
    endpoint.md
random-notes.md
~~~

### B) Azure Function handler com separação de camadas

DO
~~~ts
// src/functions/query/handler.ts
import { validateQueryRequest } from "./validator";
import { buildQueryResponse, buildErrorResponse } from "./response-builder";
import { runQuery } from "../../services/query-service";

export async function handler(request: Request): Promise<Response> {
  try {
    const input = await validateQueryRequest(request);
    const result = await runQuery(input);
    return buildQueryResponse(result);
  } catch (error) {
    return buildErrorResponse(error);
  }
}
~~~

DON'T
~~~ts
// src/functions/query/handler.ts
import { searchClient, openaiClient } from "../../services/clients";

export async function handler(request: Request): Promise<Response> {
  const body = await request.json();

  // validação, busca, prompt, chamada LLM e montagem de resposta tudo no handler
  if (!body.q || body.q.length < 3) {
    return new Response("invalid", { status: 400 });
  }

  const chunks = await searchClient.search(body.q);
  const prompt = `Use isso: ${JSON.stringify(chunks)}; Pergunta: ${body.q}`;
  const llm = await openaiClient.complete(prompt);

  return new Response(JSON.stringify({ answer: llm.text }), { status: 200 });
}
~~~

### C) React: componente reutilizável em components e página em pages

DO
~~~tsx
// src/web/src/components/ResponseCard.tsx
type ResponseCardProps = {
  answer: string;
  source?: string;
};

export function ResponseCard({ answer, source }: ResponseCardProps) {
  return (
    <section>
      <p>{answer}</p>
      {source ? <small>Fonte: {source}</small> : null}
    </section>
  );
}
~~~

~~~tsx
// src/web/src/pages/ChatPage.tsx
import { ResponseCard } from "../components/ResponseCard";

export function ChatPage() {
  return <ResponseCard answer="..." source="manual-v2.pdf" />;
}
~~~

DON'T
~~~tsx
// src/web/src/pages/ChatPage.tsx
export function ChatPage() {
  function ResponseCard() {
    return <div>...</div>;
  }

  // componente reutilizável declarado dentro da página sem necessidade
  return <ResponseCard />;
}
~~~

### D) Imports/exports consistentes

DO
~~~ts
// src/services/query-service.ts
import { search } from "./search";
import { complete } from "./completion";

export type QueryInput = { question: string };
export type QueryResult = { answer: string; sources: string[] };

export async function runQuery(input: QueryInput): Promise<QueryResult> {
  const chunks = await search(input.question);
  return complete(chunks, input.question);
}
~~~

DON'T
~~~ts
// src/services/query-service.ts
import defaultSearch from "./search";
import * as completionModule from "./completion";
import { internalFn } from "../functions/query/handler";

export default async function (x: any): Promise<any> {
  return completionModule["complete"](await defaultSearch(x), x) + internalFn;
}
~~~

### E) Localização de testes por nível

DO
~~~text
tests/
  unit/
    services/
      prompt-builder.test.ts
  integration/
    functions/
      query-handler.test.ts
~~~

DON'T
~~~text
src/
  services/
    prompt-builder.test.ts
  functions/
    query/
      integration.test.ts
~~~

---

## Anti-padrões

### 1) Handler monolítico
- Sintoma: handler contém validação, regra de negócio, integração externa e formatação de resposta.
- Impacto técnico: baixa testabilidade, alto risco de regressão, código difícil de revisar.
- Como corrigir: extrair validator, service e response-builder; manter handler como orquestrador.

### 2) Shared virando depósito genérico
- Sintoma: tudo é colocado em src/shared sem critério.
- Impacto técnico: acoplamento implícito, reutilização insegura, perda de coesão.
- Como corrigir: mover utilitários específicos para módulo/service dono; manter shared apenas para recursos transversais.

### 3) Imports cruzados entre módulos internos
- Sintoma: módulo A importa arquivo interno de módulo B (não público).
- Impacto técnico: quebra encapsulamento, refatoração cara, dependência circular.
- Como corrigir: expor API pública do módulo B ou mover responsabilidade para service compartilhado.

### 4) Testes misturados no runtime
- Sintoma: arquivos .test.ts dentro de src sem exceção formal.
- Impacto técnico: ruído no pacote de produção, confusão de navegação e tooling.
- Como corrigir: realocar para tests/unit, tests/integration ou tests/e2e com estrutura espelhada.

### 5) Nomes genéricos e ambíguos
- Sintoma: arquivos chamados utils.ts, helper.ts, data.ts em múltiplas pastas.
- Impacto técnico: baixa legibilidade, busca ruim, risco de uso incorreto.
- Como corrigir: renomear por intenção (ex.: request-parser.ts, token-budget.ts, source-attribution.ts).

### 6) Documentação fora do lugar
- Sintoma: markdown técnico dentro de src ou arquivos de spec espalhados.
- Impacto técnico: baixa rastreabilidade de decisões e planejamento.
- Como corrigir: centralizar em docs e specs conforme regra desta skill.

---

## Checklist de PR

Use este checklist em toda revisão:

- Estrutura de pastas segue padrão (src/functions, src/services, src/shared, src/web/src, tests, docs, prompts, specs).
- Nomes de pastas/arquivos seguem convenção (kebab-case no backend; PascalCase para componente React).
- Handler não contém lógica de negócio pesada.
- Validação está isolada em validator.
- Formatação de resposta está isolada em response-builder.
- Serviços externos estão em services (não no handler).
- Testes foram adicionados no nível correto (unit/integration/e2e).
- Não há testes novos dentro de src sem exceção aprovada.
- Imports não usam caminhos frágeis nem atravessam internos de outro módulo.
- Exports são explícitos e mínimos; sem export default no backend.
- Specs/docs/prompts foram atualizados no local correto quando aplicável.
- Novo módulo (se houver) possui estrutura mínima, testes mínimos e owner técnico definido.

---

## Exceções e Governança

### Quando é permitido desviar do padrão
Desvio é permitido apenas quando houver pelo menos uma condição:
1. Restrição técnica comprovada de ferramenta/plataforma.
2. Necessidade de hotfix crítico com janela curta de mitigação.
3. Experimento controlado (spike) com prazo e descarte definidos.
4. Migração incremental de legado em que aderência total imediata é inviável.

### Como registrar decisão de exceção
1. Registrar no PR uma seção Exceção de Estrutura contendo:
- regra violada,
- motivo técnico,
- risco aceito,
- plano de retorno ao padrão,
- prazo.
2. Criar ou atualizar ADR quando a exceção tiver impacto arquitetural duradouro.
3. Obter aprovação explícita do Tech Lead.
4. Abrir tarefa de follow-up vinculada ao plano de retorno.

### Política de governança
- Esta skill é mandatória para todas as demais skills.
- Divergências recorrentes devem virar melhoria desta própria skill.
- Revisões trimestrais da skill devem ocorrer com Tech Lead + representantes de Dev/QA.
