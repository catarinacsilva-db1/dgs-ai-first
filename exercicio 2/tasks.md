# Tasks — Query Endpoint

## Contexto resumido

Este documento decompõe o `plan.md` do módulo **query-endpoint** (Azure Function HTTP trigger que recebe a pergunta do atendente, busca contexto no Azure AI Search e retorna resposta gerada pelo GPT-4o com fonte) em tarefas de codificação executáveis. As confirmações externas (índice populado, system prompt finalizado) e as decisões de design pendentes (qual context budget usar — plan.md vs ADR-0002; regra de priorização por vigência — ADR-0003) deixaram de ser tickets de discovery isolados e passaram a ser **decisões embutidas dentro da task de codificação que as consome**, documentadas via comentário/constante no próprio código e referenciadas no PR correspondente. A task de observabilidade/rollout (gap não coberto pelo `plan.md`) foi removida desta versão por não corresponder a uma unidade de codificação — caso a equipe queira tratá-la, ela deve entrar como item de backlog separado, fora deste `tasks.md`.

---

## Tasks

---

**ID:** T001
**Descrição:** Criar o scaffold dos arquivos do módulo query-endpoint conforme estrutura do repositório: `src/functions/query/handler.ts`, `validator.ts`, `response-builder.ts` e `src/services/search.ts`, `completion.ts`, `prompt-builder.ts`, `response-validator.ts`, todos com exports vazios/stubs e tipagem inicial.
**Critérios de aceite:**
- Todos os 7 arquivos existem nos caminhos indicados.
- O projeto compila (`tsc --noEmit`) sem erros após a criação dos stubs.
**Dependências:**
- Nenhuma
**Estimativa:** P

---

**ID:** T002
**Descrição:** Implementar utilitário de retry com exponential backoff reutilizável para chamadas a serviços Azure (Azure OpenAI e Azure AI Search), em `src/shared/`.
**Critérios de aceite:**
- A função aceita número máximo de tentativas e backoff configuráveis.
- Teste unitário simula 2 falhas seguidas de sucesso e valida que a 3ª tentativa retorna o resultado esperado.
- Após exceder o número máximo de tentativas, a função propaga o erro original.
**Dependências:**
- T001
**Estimativa:** M

---

**ID:** T003
**Descrição:** Implementar o schema Zod de validação do input do endpoint (`validator.ts`), validando o corpo da requisição POST `/api/query` (pergunta do atendente).
**Critérios de aceite:**
- Requisição com campo `pergunta` ausente ou vazio é rejeitada com erro de validação.
- Requisição válida passa pela validação sem erros.
- Tipos TypeScript do input são inferidos a partir do schema Zod (`z.infer`).
**Dependências:**
- T001
**Estimativa:** P

---

**ID:** T004
**Descrição:** Implementar `handler.ts` como HTTP trigger do Azure Functions v4 para a rota POST `/api/query`, integrando a validação de input (T003) e instrumentando structured logging com pino na entrada e saída da requisição.
**Critérios de aceite:**
- Requisição com input inválido retorna status 400 com mensagem de erro estruturada.
- Requisição com input válido segue para a próxima etapa do fluxo (pode retornar stub nesta etapa).
- Cada requisição gera um log de entrada e um de saída via pino, correlacionáveis por um `requestId` comum.
**Dependências:**
- T001, T003
**Estimativa:** M

---

**ID:** T005
**Descrição:** Implementar em `search.ts` a geração do embedding da pergunta do atendente via Azure OpenAI, utilizando o utilitário de retry (T002) e instrumentando log de início/fim da chamada e log `warn` em cada tentativa de retry.
**Critérios de aceite:**
- A função recebe uma string (pergunta) e retorna um vetor de embedding.
- Em caso de falha transitória simulada da API, o retry de T002 é acionado e cada tentativa gera log `warn` via pino.
**Dependências:**
- T001, T002
**Estimativa:** M

---

**ID:** T006
**Descrição:** Implementar em `search.ts` a busca dos top-5 chunks no Azure AI Search a partir do embedding gerado (T005), utilizando o retry de T002 e instrumentando log de início/fim da busca e log `warn` em cada retry. **Antes de integrar contra o índice real, confirmar com o responsável pelo pipeline de ingestão que o índice está populado** e registrar essa confirmação no PR (commit message ou descrição); se o índice ainda não estiver populado, implementar contra mock e marcar a integração real como bloqueada até a confirmação.
**Critérios de aceite:**
- A confirmação (ou o bloqueio, se aplicável) de que o índice está populado está registrada no PR desta task.
- A função retorna até 5 chunks ordenados por relevância (score), incluindo o metadado de vigência de cada chunk.
- Em caso de índice vazio, a função retorna lista vazia sem lançar exceção não tratada.
- Cada tentativa de retry gera log `warn` via pino.
**Dependências:**
- T001, T002, T005
**Estimativa:** M

---

**ID:** T007
**Descrição:** Implementar em `prompt-builder.ts` a função de resolução de conflito de vigência (ADR-0003): a partir dos chunks retornados por T006, decidir e documentar via comentário/JSDoc na própria função a regra de priorização adotada (ex.: "em caso de conflito sobre o mesmo tópico, mantém-se o chunk com data de vigência mais recente"), e aplicá-la para produzir o subconjunto sem conflito. Instrumentar log `info` via pino sempre que um chunk for descartado por conflito de vigência, incluindo o motivo.
**Critérios de aceite:**
- A regra de priorização adotada está documentada via comentário/JSDoc na função, referenciando a ADR-0003.
- Dado um conjunto de chunks sem conflito, a função retorna o conjunto inalterado.
- Dado um conjunto com chunks conflitantes sobre o mesmo tópico, a função mantém apenas o chunk definido pela regra documentada e descarta os demais.
- Cada chunk descartado gera um log `info` via pino com o motivo do descarte.
**Dependências:**
- T002, T006
**Estimativa:** M

---

**ID:** T008
**Descrição:** Implementar em `prompt-builder.ts` a função de truncamento por context budget: a partir dos chunks já filtrados por vigência (T007), adotar como padrão o valor da ADR-0002 (~4K tokens para system prompt + ~8K para chunks) — já que diverge do valor informado no `plan.md` (~2K) — definindo o budget como constante nomeada e documentada (ex.: `SYSTEM_PROMPT_BUDGET_TOKENS = 4000 // conforme ADR-0002`), e removendo os chunks de menor score até caber no orçamento. Instrumentar log `info` via pino sempre que um chunk for descartado por exceder o budget.
**Critérios de aceite:**
- O valor de budget usado está definido como constante nomeada no código, com comentário referenciando a fonte da decisão (ADR-0002).
- Quando os chunks filtrados cabem no budget, a função retorna o conjunto inalterado.
- Quando excedem o budget, os chunks de menor score são removidos primeiro, até caber no limite.
- Cada chunk descartado por budget gera um log `info` via pino.
**Dependências:**
- T007
**Estimativa:** M

---

**ID:** T009
**Descrição:** Implementar em `prompt-builder.ts` a função de montagem final do prompt, lendo o system prompt diretamente de `/prompts/system-prompt.md` (a versão presente no repositório no momento da implementação) e concatenando-o com os chunks resultantes de T008 e a pergunta do atendente, no formato esperado pelo GPT-4o. Registrar no PR o commit/hash do `system-prompt.md` usado como referência.
**Critérios de aceite:**
- O commit/hash do `system-prompt.md` usado está referenciado no PR desta task.
- O prompt final contém as três partes (system prompt, chunks, pergunta) na ordem correta.
- O prompt final não excede o limite total de tokens definido em T008 (validado por contagem de tokens).
**Dependências:**
- T001, T008
**Estimativa:** M

---

**ID:** T010
**Descrição:** Implementar `completion.ts` para enviar o prompt montado (T009) ao GPT-4o, utilizando o retry de T002 e instrumentando log de início/fim da chamada, log `warn` em cada retry e log `error` com stack trace em falha não recuperável.
**Critérios de aceite:**
- A chamada retorna o texto de resposta do modelo.
- Em caso de erro 429/5xx simulado, o retry de T002 é acionado e cada tentativa gera log `warn`.
- Timeout configurável é respeitado; falha não recuperável gera log `error` com stack trace.
**Dependências:**
- T002, T009
**Estimativa:** M

---

**ID:** T011
**Descrição:** Implementar `response-builder.ts` para montar a resposta final do endpoint, incluindo o texto de resposta do GPT-4o e o campo `source_document` referenciando o(s) chunk(s) efetivamente usado(s) no prompt (T009).
**Critérios de aceite:**
- A resposta montada contém os campos `resposta` e `source_document`.
- `source_document` referencia exatamente o(s) chunk(s) incluído(s) no prompt final.
**Dependências:**
- T010
**Estimativa:** P

---

**ID:** T012
**Descrição:** Implementar o schema Zod de validação do output (`response-validator.ts`) e integrá-lo em `handler.ts` (T004) antes do retorno ao atendente.
**Critérios de aceite:**
- Resposta malformada (ex.: `source_document` ausente) é detectada antes do retorno ao cliente.
- Resposta válida passa pela validação e é retornada com status 200.
**Dependências:**
- T004, T011
**Estimativa:** P

---

**ID:** T013
**Descrição:** Escrever testes unitários para `validator.ts` (input), cobrindo pergunta ausente, pergunta vazia e input válido.
**Critérios de aceite:**
- Suíte cobre os 3 cenários listados e todos passam em execução local (`vitest run`).
**Dependências:**
- T003
**Estimativa:** P

---

**ID:** T014
**Descrição:** Escrever testes unitários para `response-validator.ts` (output), cobrindo resposta sem `source_document` e resposta válida.
**Critérios de aceite:**
- Suíte cobre os 2 cenários listados e todos passam em execução local.
**Dependências:**
- T012
**Estimativa:** P

---

**ID:** T015
**Descrição:** Escrever testes unitários para a função de resolução de vigência em `prompt-builder.ts` (T007), cobrindo conjunto sem conflito e conjunto com chunks conflitantes.
**Critérios de aceite:**
- Teste confirma que conjunto sem conflito retorna inalterado.
- Teste confirma que, havendo conflito, apenas o chunk definido pela regra documentada em T007 permanece.
**Dependências:**
- T007
**Estimativa:** P

---

**ID:** T016
**Descrição:** Escrever testes unitários para a função de truncamento por budget em `prompt-builder.ts` (T008), cobrindo conjunto dentro do limite e conjunto que excede o limite.
**Critérios de aceite:**
- Teste confirma que conjunto dentro do budget retorna inalterado.
- Teste confirma que, excedendo o budget, os chunks de menor score são removidos até caber no limite definido em T008.
**Dependências:**
- T008
**Estimativa:** P

---

**ID:** T017
**Descrição:** Escrever testes unitários para a função de montagem final do prompt em `prompt-builder.ts` (T009), cobrindo a ordem das partes e o respeito ao budget total.
**Critérios de aceite:**
- Teste confirma a ordem correta (system prompt, chunks, pergunta) no prompt final.
- Teste confirma que o prompt final não excede o limite total de tokens.
**Dependências:**
- T009
**Estimativa:** P

---

**ID:** T018
**Descrição:** Escrever testes unitários para `response-builder.ts`, cobrindo a presença e o formato correto do campo `source_document`.
**Critérios de aceite:**
- Teste confirma que `source_document` está presente e referencia o chunk correto para um cenário com 1 chunk relevante.
- Comportamento para o cenário sem chunks relevantes está coberto (resposta sem fonte ou fallback — sinalizar como **A confirmar** se não definido pela equipe).
**Dependências:**
- T011
**Estimativa:** P

---

**ID:** T019
**Descrição:** Escrever testes de integração com mocks (msw) cobrindo o fluxo completo: `handler` → `search` (embedding + busca) → `prompt-builder` (vigência + budget + montagem) → `completion` → `response-builder`.
**Critérios de aceite:**
- Teste simula uma requisição POST `/api/query` completa com mocks de Azure OpenAI e Azure AI Search, validando a resposta final ponta a ponta.
- Teste cobre ao menos um cenário de falha (ex.: Azure AI Search indisponível) validando tratamento e retorno estruturado do erro.
**Dependências:**
- T004, T006, T007, T008, T009, T010, T011, T012
**Estimativa:** G

---

**ID:** T020
**Descrição:** Escrever teste e2e do endpoint POST `/api/query`, exercitando o fluxo real contra os serviços Azure (uso controlado, dado o consumo de tokens).
**Critérios de aceite:**
- Teste e2e é executado isoladamente (script/comando dedicado, fora do `test` padrão de CI).
- Teste valida uma pergunta de referência (golden query) e confirma que a resposta contém `source_document` coerente.
**Dependências:**
- T019
**Estimativa:** M

---

**ID:** T021
**Descrição:** Atualizar `/prompts/prompt-changelog.md` registrando data, autor, motivo e resultado esperado, caso o budget definido em T008 ou a referência de `system-prompt.md` usada em T009 exijam alteração do prompt versionado.
**Critérios de aceite:**
- Se houver alteração do system prompt, uma nova entrada é adicionada ao changelog com os 4 campos exigidos.
- Se não houver alteração, este fato é registrado explicitamente como "Nenhuma alteração necessária".
**Dependências:**
- T008, T009
**Estimativa:** P

---

**ID:** T022
**Descrição:** Executar a validação final do módulo query-endpoint: revisar os critérios de aceite de todas as tasks de implementação, rodar a suíte completa de testes (unit + integration) e confirmar cobertura de todas as decisões do `plan.md`.
**Critérios de aceite:**
- Suíte de testes unitários e de integração executa com 100% de sucesso (`vitest run`).
- Checklist de prontidão (seção abaixo) está totalmente marcado.
- Nenhum item da Matriz de Cobertura está sem task associada.
**Dependências:**
- T012, T013, T014, T015, T016, T017, T018, T019
**Estimativa:** M

---

## Matriz de cobertura

| Seção do plan.md | IDs das tasks |
|---|---|
| Approach — passo 1 (recebe pergunta via POST /api/query) | T003, T004 |
| Approach — passo 2 (embedding via Azure OpenAI) | T005 |
| Approach — passo 3 (busca top-5 chunks no Azure AI Search) | T006 *(inclui confirmação de índice populado)* |
| Approach — passo 4 (monta prompt, context budget) | T008, T009, T016, T017 *(inclui decisão de budget)* |
| Approach — passo 5 (envia GPT-4o, retorna com source_document) | T010, T011, T012, T018 |
| Technical Decisions — TypeScript / Azure Functions v4 | T001, T004 |
| Technical Decisions — Zod (input/output) | T003, T012, T013, T014 |
| Technical Decisions — retry com exponential backoff | T002, T005, T006, T010 |
| Technical Decisions — structured logging (pino) | T004, T005, T006, T007, T008, T010 *(critério de aceite embutido na task de implementação)* |
| Prior Decisions — context budget (ADR-0002) | T008, T009, T016, T017 *(decisão embutida na task de implementação)* |
| Prior Decisions — documentos contraditórios / vigência (ADR-0003) | T007, T015 *(regra embutida na task de implementação)* |
| Prior Decisions — system prompt versionado | T009, T021 *(referência embutida na task de implementação)* |
| Dependencies — índice Azure AI Search populado | T006 *(confirmação embutida na task de implementação)* |
| Dependencies — system prompt finalizado | T009 *(confirmação embutida na task de implementação)* |
| Validação geral do módulo | T022 |

---

## Caminho crítico

```
T001 → T002 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T019 → T020 → T022
```

- **T006 → T007 → T008 → T009** é a cadeia mais longa e mais arriscada: cada task carrega tanto a implementação quanto a decisão/confirmação que antes vivia em um ticket separado. Um atraso na confirmação do índice (T006) ou na decisão de budget (T008) atrasa a cadeia inteira até T022 — não há mais um ticket de discovery "fora do caminho" para absorver esse atraso.
- **T002 (retry)** bloqueia T005, T006 e T010 — infraestrutura compartilhada mais crítica.
- **T019 (integração)** é o último ponto de validação automatizada antes de T022; qualquer falha aqui propaga atraso para o fechamento do módulo.

---

## Checklist final de prontidão

- [ ] Scaffold de arquivos criado e projeto compilando (T001)
- [ ] Utilitário de retry implementado e testado (T002)
- [ ] Validação de input e output implementadas, com logging integrado (T003, T004, T012)
- [ ] Embedding implementado, com retry e logging (T005)
- [ ] Busca de chunks implementada, com confirmação de índice populado registrada no PR, retry e logging (T006)
- [ ] Resolução de vigência implementada, com regra documentada no código (T007)
- [ ] Truncamento por budget implementado, com valor de budget documentado como constante (T008)
- [ ] Montagem final do prompt implementada, com hash do system-prompt.md referenciado no PR (T009)
- [ ] Chamada ao GPT-4o com retry e logging implementada (T010)
- [ ] Resposta final com `source_document` implementada (T011)
- [ ] Testes unitários de validators, prompt-builder e response-builder passando (T013–T018)
- [ ] Testes de integração e e2e passando (T019, T020)
- [ ] Prompt-changelog atualizado, se aplicável (T021)
- [ ] Validação final executada e matriz de cobertura sem lacunas (T022)
