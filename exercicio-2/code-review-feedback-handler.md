# Code Review — `feedback-handler.ts`

**Módulo revisado:** `feedback-handler.ts` (endpoint de feedback, Azure Functions)
**Gerado por:** Copilot
**Revisor:** Assistente de IA (revisão crítica solicitada pelo time)
**Contexto:** Endpoint identificado durante o desenvolvimento como não conformidade com o AGENTS.md — não usou Zod para validação e logou dados sensíveis do atendente.

---

## Código revisado

```typescript
// feedback-handler.ts — gerado pelo Copilot
import { app, HttpRequest, HttpResponseInit } from '@azure/functions';

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  const body = await request.json() as any;

  const feedback = {
    queryId: body.queryId,
    rating: body.rating,
    comment: body.comment,
    attendantEmail: body.attendantEmail,
    timestamp: new Date().toISOString()
  };

  console.log('Feedback recebido:', JSON.stringify(feedback));

  const { CosmosClient } = require('@azure/cosmos');
  const client = new CosmosClient(process.env.COSMOS_CONNECTION_STRING);
  const database = client.database('novatech');
  const container = database.container('feedbacks');

  await container.items.create(feedback);

  return { status: 200, body: 'OK' };
}

app.http('feedback', {
  methods: ['POST'],
  handler: feedbackHandler
});
```

---

## Resumo executivo

| Severidade | Qtde de problemas |
|---|---|
| 🔴 Crítico | 4 |
| 🟠 Grave | 5 |
| 🟡 Moderado | 3 |
| 🟢 Simples | 2 |

Nenhum dos problemas críticos é sutil — todos seriam capturados por um schema Zod exigido pelo AGENTS.md e por uma revisão humana de poucos minutos antes do merge.

---

## 🔴 Crítico

### 1. Ausência total de validação de input
**Linha:** 7 — `const body = await request.json() as any;`

Não há schema Zod nem qualquer validação dos campos antes de seguir para persistência. Viola diretamente a regra do AGENTS.md ("não usou Zod"). `rating` pode vir fora de range, `queryId` pode não existir, campos podem estar ausentes ou com tipos errados — nada disso é capturado antes de ir para o banco.

### 2. Log de dados sensíveis do atendente
**Linha:** 17 — `console.log('Feedback recebido:', JSON.stringify(feedback));`

Grava `attendantEmail` e `comment` em texto puro nos logs. É o problema de governança citado no cenário: logs têm retenção longa e acesso mais amplo que o banco de dados, configurando vazamento de PII por design.

### 3. Nenhum tratamento de erro
**Linhas:** 7, 19–24

Não há `try/catch` em lugar nenhum: `request.json()`, criação do `CosmosClient` e `container.items.create` podem lançar exceção (JSON inválido, env var ausente, throttling 429, erro de rede). Qualquer falha sobe sem tratamento, gerando um 500 genérico (ou expondo stack trace), sem sinalização estruturada para o chamador (bot do Teams).

### 4. Ausência de autenticação/autorização
**Linhas:** 29–32

`app.http('feedback', { methods: ['POST'], handler: feedbackHandler })` não define `authLevel`. Qualquer requisição anônima pode submeter feedback com qualquer `queryId`/`attendantEmail`, permitindo spoofing de identidade e poluição de dados.

---

## 🟠 Grave

### 5. `CosmosClient` instanciado a cada requisição
**Linhas:** 19–22

`require` + `new CosmosClient(...)` dentro do handler abre uma conexão nova por invocação, esgotando o connection pool e adicionando latência desnecessária. Deveria ser um singleton no escopo do módulo.

### 6. Nenhuma resiliência a throttling do Cosmos
**Linha:** 24

`container.items.create(feedback)` sem retry/backoff. Sob carga (ex.: durante a demonstração para a diretoria), um 429 do Cosmos causa perda silenciosa de feedback.

### 7. Resposta não estruturada
**Linha:** 26 — `return { status: 200, body: 'OK' };`

Corpo é uma string livre, sem `Content-Type: application/json`, sem contrato formal. Contradiz o objetivo desta fase de reforçar o harness com *structured outputs*.

### 8. `require` misturado com `import`, tipagem `any`
**Linhas:** 7, 19

O projeto declara `tsconfig strict: true`, mas `body` é `any` e `CosmosClient` é importado via `require` sem tipos — anula as garantias de tipo que o `strict` deveria oferecer.

### 9. Sem proteção de idempotência
**Linha:** 24

Retry de rede (comum em integrações com bots) pode causar duplo `items.create` para o mesmo feedback, sem chave de idempotência nem uso de `upsert`.

---

## 🟡 Moderado

### 10. Nenhuma validação de existência de env var
**Linha:** 20 — `process.env.COSMOS_CONNECTION_STRING`

Usado direto sem checar se está definido. Se ausente, o erro que sobe do SDK do Cosmos é críptico e difícil de diagnosticar em produção.

### 11. Estratégia de partition key não explícita
**Linhas:** 9–15, 24

Não há indicação de qual campo do documento `feedback` é a partition key do container `feedbacks`. Se o container exigir uma chave ausente no objeto, a escrita falha em runtime.

### 12. Nenhuma verificação de que `queryId` é válido
**Linha:** 10

O feedback é aceito para qualquer `queryId`, sem checar se corresponde a uma consulta real já registrada, abrindo espaço para dados órfãos ou inconsistentes.

---

## 🟢 Simples

### 13. Comentário de autoria deixado no código
**Linha:** 1 — `// feedback-handler.ts — gerado pelo Copilot`

Artefato de geração sem valor de documentação, deve ser removido antes do merge.

### 14. `require` inline deveria ser `import` no topo do arquivo
**Linha:** 19

Por convenção de estilo, independente da correção do item #5, o import deveria estar junto aos demais no topo do arquivo.

---

## Plano de correção

| Prioridade | Itens | Ação recomendada |
|---|---|---|
| Bloqueia merge | #1, #2, #3, #4 | Schema Zod para validar o body; remover/mascarar PII do log; envolver a lógica em try/catch com resposta de erro estruturada; definir `authLevel` explícito e verificar identidade do chamador. |
| Antes do go-live | #5, #6, #7, #8, #9 | Singleton do `CosmosClient`; retry com backoff; resposta JSON tipada; remover `any`/`require`; chave de idempotência ou `upsert`. |
| Desejável | #10, #11, #12 | Fail-fast em env var ausente; confirmar partition key do container; validar `queryId` contra a store de queries. |
| Cleanup | #13, #14 | Ajustes de estilo. |
