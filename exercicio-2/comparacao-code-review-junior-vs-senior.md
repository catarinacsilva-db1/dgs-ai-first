# Comparação — Code Review do Dev Júnior vs. Code Review de Referência

**Módulo avaliado:** `feedback-handler.ts`
**Reviews comparadas:**
1. `Code review - DEV.md` — review feita por um desenvolvedor de nível júnior.
2. Review de referência — feita pelo assistente de IA em [code-review-feedback-handler.md](code-review-feedback-handler.md).

**Objetivo:** medir a cobertura da review júnior frente aos problemas reais do módulo, e usar o gap como insumo de mentoria e como argumento para reforçar o harness (validação estruturada + human-in-the-loop) em vez de depender só de revisão manual.

---

## Tabela comparativa

| Problema | Review de referência | Review do Dev Júnior |
|---|---|---|
| Falta de validação de input (Zod) | 🔴 Crítico | ❌ Não identificado |
| Log de dados sensíveis (`attendantEmail`, `comment`) | 🔴 Crítico | Rebaixado — citado apenas como "usar logging em vez de `console.log`" (🟢 Simples), sem mencionar que o dado é sensível |
| Falta de try/catch | 🔴 Crítico | 🔴 Crítico ✅ (única classificação idêntica) |
| Falta de autenticação/`authLevel` | 🔴 Crítico | ❌ Não identificado |
| `CosmosClient` recriado a cada request | 🟠 Grave | ❌ Não identificado |
| Falta de retry/backoff para throttling do Cosmos | 🟠 Grave | ❌ Não identificado |
| Resposta não estruturada (`status: 200, body: 'OK'`) | 🟠 Grave | 🟠 Grave — mas o foco foi só "usar 201 em vez de 200", sem conectar ao problema de *structured outputs* |
| Tipagem `any` no body | 🟠 Grave | 🟠 Grave ✅ |
| `require` misturado com `import` | 🟢 Simples | 🟢 Simples ✅ |
| Falta de idempotência | 🟠 Grave | ❌ Não identificado |
| Falta de validação de env var (`COSMOS_CONNECTION_STRING`) | 🟡 Moderado | ❌ Não identificado |
| Partition key não explícita no container | 🟡 Moderado | ❌ Não identificado |
| `queryId` não validado contra query real | 🟡 Moderado | ❌ Não identificado |
| Comentário de autoria deixado no código | 🟢 Simples | ❌ Não identificado |

**Cobertura do dev júnior: 3 de 14 pontos (~21%)** — e mesmo esses 3 vieram com classificação mais branda ou com o motivo errado.

---

## O gap mais importante

O `console.log` com `attendantEmail` e `comment` é o item que o time já sabia ser uma violação real do AGENTS.md ("logou dados sensíveis do atendente"). A review júnior tratou isso como um problema de **estilo de logging** ("`console.log` em vez de logging apropriado") — não como exposição de PII. É o equivalente a revisar um vazamento de dados como se fosse só uma preferência de formatação. Se essa review fosse a única barreira antes do merge, o vazamento passaria.

Da mesma forma, a ausência completa de validação com Zod — a outra violação explícita do AGENTS.md citada no cenário — nem aparece na review júnior. Os dois problemas mais graves e mais diretamente ligados aos guardrails do time (governança, privacidade, contrato de dados) foram os dois que a review júnior não capturou ou subestimou.

---

## Padrão geral observado

A review júnior está concentrada em **robustez de código e sintaxe**:
- try/catch
- tipagem (`any`)
- status HTTP
- `require` vs `import`

Esses são sinais que um linter ou TypeScript em modo strict já ajudariam a capturar. A review júnior não olha para:

- **Segurança** — ausência de autenticação/autorização, dados sensíveis em log
- **Governança/conformidade** — exigência de Zod pelo AGENTS.md, exposição de PII (relevante sob LGPD)
- **Confiabilidade operacional** — singleton de client, retry/backoff, idempotência

---

## Conclusão e uso recomendado

Este gap é consistente com o motivo pelo qual o time está reforçando o harness nesta fase: revisão humana isolada — especialmente de nível júnior — não é suficiente como única camada de defesa. Por isso a estratégia correta é combinar:

1. **Validação estruturada (structured outputs / Zod no CI)** — para pegar automaticamente a ausência de schema, em vez de depender de alguém notar isso na review.
2. **Regras de lint/CI dedicadas** — ex.: proibir `console.log` de objetos que contenham campos de PII (`attendantEmail`, `comment`), e falhar o build se um endpoint não usar Zod.
3. **Mentoria pontual** — usar este comparativo para explicar ao dev júnior *por que* log de PII é crítico e não estilo, e por que ausência de validação de input é crítico e não um nice-to-have.

Depender apenas de review manual (mesmo bem-intencionada) deixou passar exatamente os dois itens que o AGENTS.md formalizou como regra do time — reforçando que o harness (validação automática + gate humano no ponto certo) precisa capturar isso antes do merge, não depois.
