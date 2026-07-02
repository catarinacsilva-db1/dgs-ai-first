# Code Review — `response-validator.ts` (+ schema em `response-builder.ts`)

> O schema Zod (`queryResponseSchema`) é definido em `src/functions/query/response-builder.ts` e importado por `response-validator.ts`. Como os objetivos 1, 4 e 5 do review são sobre o schema, as correções abaixo cobrem os dois arquivos.

## Seção 1: Problemas encontrados

### 1. `confidence_score` sem limites de faixa (0–1) — **Severidade: Alta**
**Onde:** `response-builder.ts`, schema: `confidence_score: z.number().finite()`
**Impacto:** o schema aceita qualquer número finito (`-50`, `999`, `1.5`, `-0.001`). Um valor fora de `[0, 1]` quebra qualquer lógica downstream que trate `confidence_score` como probabilidade (thresholds, ordenação, exibição em %). Isso é aceito silenciosamente porque `.strict()` só barra campos extras, não valores fora de faixa.
**Objetivo relacionado:** 5.

### 2. `source_document` vazio/whitespace passa como `isValid: true` em `validateStructuredOutput` — **Severidade: Alta**
**Onde:** `response-builder.ts` (`source_document: z.string()`) + `response-validator.ts:51-75` (`validateStructuredOutput`)
**Impacto:** o schema só rejeita `source_document` ausente/`null`/tipo errado. Uma string vazia `""` ou só espaços `"   "` passa no `safeParse` e `validateStructuredOutput` retorna `isValid: true` com esse payload. A checagem de trim só existe em `applyGuardrails` (chamada depois). Qualquer código que use `validateStructuredOutput` isoladamente (sem passar por `applyGuardrails`) trata uma resposta sem fonte real como válida — viola diretamente o requisito "source_document obrigatório e deve ser preenchido".
**Objetivo relacionado:** 4.

### 3. Falso negativo: variações de linguagem do padrão de risco não são detectadas — **Severidade: Crítica (bypass de guardrail de segurança)**
**Onde:** `response-validator.ts:29-30`
```ts
const DANGEROUS_CARGO_PATTERN = /carga perigosa/i;
const RETURN_PATTERN = /devolu[cç][ãa]o/i;
```
**Impacto:**
- Não cobre **plural** (`cargas perigosas`, `materiais perigosos`).
- Não cobre **sinônimos** (`material perigoso`, `produto perigoso`, `carga tóxica/inflamável/explosiva/radioativa`).
- Não cobre **formas verbais** de devolução (`devolver`, `devolvida`, `devolvido`) — só casa o substantivo `devolução`/`devolucao`. Frase real de alto risco como `"Você pode devolver a carga perigosa sem problema."` **não é bloqueada**, pois `RETURN_PATTERN` não casa com `devolver`.
- Não é tolerante a texto sem acentuação correta em todas as variações (parcialmente coberto, mas de forma frágil com classes de caracteres `[ãa]`/`[cç]`).
Um LLM pode facilmente parafrasear a resposta perigosa de forma a escapar do guardrail.
**Objetivo relacionado:** 2, 3.

### 4. Falso positivo: `POSITIVE_RETURN_PATTERN` ignora negação e não respeita fronteira de frase — **Severidade: Alta**
**Onde:** `response-validator.ts:31-32`
```ts
const POSITIVE_RETURN_PATTERN =
  /(devolu[cç][ãa]o).*(pode|poss[ií]vel|permitid[ao]?|autorizad[ao]?)|.../i;
```
**Impacto:** o `.*` é **sem limite** e não respeita ponto final. Duas consequências reais:
- **Negação ignorada:** `"A devolução de carga perigosa não é permitida."` (uma negação correta e segura) casa com o regex porque ele só procura a palavra `permitida` em algum ponto depois de `devolução`, sem checar se há um `não` no meio. Resultado: `affirmsDangerousReturn` retorna `true` para uma frase que **nega** a ação, e a resposta correta acaba bloqueada (perda de informação legítima).
- **Vazamento entre frases:** um `permitido`/`autorizado` em uma frase totalmente não relacionada, mais adiante no mesmo texto, pode "contaminar" a avaliação de uma frase anterior sobre carga perigosa, gerando bloqueio (ou liberação) por engano.
**Objetivo relacionado:** 3.

### 5. Schema já usa `.strict()` — **OK, sem ação** (verificado, não é bug)
O objeto já é `.strict()`, então campos extras não previstos já são rejeitados (`ZodError` com `unrecognized_keys`), caindo em `INVALID_SCHEMA_MESSAGE`. Mantido como está; adicionei um teste explícito para não regredir.

---

## Seção 2: Código corrigido

### `src/functions/query/response-builder.ts`
```ts
import { z } from "zod";

export const queryResponseSchema = z
  .object({
    answer: z.string(),
    source_document: z
      .string()
      .trim()
      .min(1, "source_document deve ser uma string nao vazia."),
    confidence_score: z
      .number()
      .finite()
      .min(0, "confidence_score deve ser >= 0.")
      .max(1, "confidence_score deve ser <= 1."),
  })
  .strict();

export type QueryResponsePayload = z.infer<typeof queryResponseSchema>;

export function buildQueryResponse(
  payload: QueryResponsePayload,
): QueryResponsePayload {
  return queryResponseSchema.parse(payload);
}
```

### `src/services/response-validator.ts`
```ts
import {
  queryResponseSchema,
  type QueryResponsePayload,
} from "../functions/query/response-builder";

export const INVALID_SCHEMA_MESSAGE =
  "Resposta rejeitada: o JSON nao segue o schema estruturado esperado.";
export const MISSING_SOURCE_DOCUMENT_MESSAGE =
  "Resposta rejeitada: source_document e obrigatorio e deve ser preenchido.";
export const DANGEROUS_RETURN_BLOCK_MESSAGE =
  "Resposta bloqueada: nao e permitido afirmar devolucao para carga perigosa.";

export type QueryResponseValidationStatus = "accepted" | "rejected" | "blocked";

export interface StructuredOutputValidationResult {
  isValid: boolean;
  payload: QueryResponsePayload | null;
  reason: string;
}

export interface QueryResponseValidationResult {
  status: QueryResponseValidationStatus;
  payload: QueryResponsePayload;
  reason: string;
}

/**
 * Normaliza texto para comparação: remove acentuação/diacriticos e caixa,
 * para que as regras de deteccao nao dependam de o modelo escrever
 * "devolução" vs "devolucao", "não" vs "nao", etc.
 */
function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(new RegExp("[\\u0300-\\u036f]", "g"), "")
    .toLowerCase();
}

function splitClauses(normalizedText: string): string[] {
  return normalizedText
    .split(/[.!?;\n]+/)
    .map((clause) => clause.trim())
    .filter((clause) => clause.length > 0);
}

// Substantivo/adjetivo de carga perigosa: cobre singular/plural e sinonimos
// (material, produto, mercadoria, substancia) x (perigoso, toxico,
// inflamavel, explosivo, radioativo, corrosivo), com ate 3 palavras entre
// o substantivo e o adjetivo para cobrir fraseado indireto
// ("carga classificada como perigosa").
const DANGEROUS_CARGO_PATTERN =
  /\b(cargas?|materiais?|produtos?|mercadorias?|substancias?)\b(?:\s+\w+){0,3}?\s+\b(perigos[ao]s?|toxic[ao]s?|inflamave(?:l|is)|explosiv[ao]s?|radioativ[ao]s?|corrosiv[ao]s?)\b/;

// Formas nominais e verbais de "devolucao": substantivo, verbo (devolver/
// devolvida/devolvendo), e sinonimos (retorno/restituicao).
const RETURN_PATTERN =
  /\b(devolucoes|devolucao|devolv\w*|retorn\w*|restitu\w*)\b/;

// Negacao "forte" (por si so ja indica proibicao, ex: "proibida",
// "vedada"), usada como sinal de ausencia de afirmacao clara.
const NEGATION_PATTERN =
  /\b(nao|nunca|jamais|impossivel|proibid[ao]s?|vedad[ao]s?|indevid[ao]s?)\b/;

// Palavras que, isoladas, afirmam permissao.
const PERMISSION_PATTERN =
  /\b(pode|podem|possivel|permitid[ao]s?|autorizad[ao]s?|liberad[ao]s?|dispensad[ao]s?)\b/;

// Negacao proxima (ate 4 palavras) de uma palavra de permissao, cobrindo
// "nao e permitida", "nao pode", "nunca sera autorizada", etc. Necessario
// para nao confundir uma negacao ("nao e permitida") com uma afirmacao.
const NEGATED_PERMISSION_PATTERN =
  /\b(nao|nunca|jamais)\b(?:\s+\w+){0,4}?\s+\b(pode|podem|possivel|permitid[ao]s?|autorizad[ao]s?|liberad[ao]s?|dispensad[ao]s?)\b/;

// Duplo-negativo comum em PT-BR que na pratica AFIRMA permissao
// ("nao ha impedimento" == "e permitido").
const DOUBLE_NEGATIVE_AFFIRMATION_PATTERN =
  /\bnao\s+ha\b(?:\s+\w+){0,4}?\s+\b(impedimentos?|problemas?|restric(?:ao|oes)|objec(?:ao|oes)|obstaculos?)\b/;

function buildFallbackPayload(message: string): QueryResponsePayload {
  return {
    answer: message,
    source_document: "N/A",
    confidence_score: 0,
  };
}

function clauseMentionsDangerousReturn(clause: string): boolean {
  return DANGEROUS_CARGO_PATTERN.test(clause) && RETURN_PATTERN.test(clause);
}

function mentionsDangerousReturnScenario(answer: string): boolean {
  return splitClauses(normalize(answer)).some(clauseMentionsDangerousReturn);
}

function clauseAffirmsReturn(clause: string): boolean {
  if (DOUBLE_NEGATIVE_AFFIRMATION_PATTERN.test(clause)) {
    return true;
  }
  return (
    PERMISSION_PATTERN.test(clause) && !NEGATED_PERMISSION_PATTERN.test(clause)
  );
}

function affirmsDangerousReturn(answer: string): boolean {
  return splitClauses(normalize(answer)).some(
    (clause) => clauseMentionsDangerousReturn(clause) && clauseAffirmsReturn(clause),
  );
}

function hasClearDenial(answer: string): boolean {
  return splitClauses(normalize(answer)).some(
    (clause) => clauseMentionsDangerousReturn(clause) && NEGATION_PATTERN.test(clause),
  );
}

export function validateStructuredOutput(
  response: unknown,
): StructuredOutputValidationResult {
  const parsed = queryResponseSchema.safeParse(response);

  if (parsed.success) {
    return {
      isValid: true,
      payload: parsed.data,
      reason: "Structured output valido.",
    };
  }

  const hasSourceDocumentIssue = parsed.error.issues.some(
    (issue) => issue.path[0] === "source_document",
  );

  return {
    isValid: false,
    payload: null,
    reason: hasSourceDocumentIssue
      ? MISSING_SOURCE_DOCUMENT_MESSAGE
      : INVALID_SCHEMA_MESSAGE,
  };
}

export function applyGuardrails(
  payload: QueryResponsePayload,
): QueryResponseValidationResult {
  if (payload.source_document.trim().length === 0) {
    return {
      status: "rejected",
      payload: buildFallbackPayload(MISSING_SOURCE_DOCUMENT_MESSAGE),
      reason: MISSING_SOURCE_DOCUMENT_MESSAGE,
    };
  }

  if (
    mentionsDangerousReturnScenario(payload.answer)
    && (affirmsDangerousReturn(payload.answer)
      || !hasClearDenial(payload.answer))
  ) {
    return {
      status: "blocked",
      payload: buildFallbackPayload(DANGEROUS_RETURN_BLOCK_MESSAGE),
      reason: DANGEROUS_RETURN_BLOCK_MESSAGE,
    };
  }

  return {
    status: "accepted",
    payload,
    reason: "Structured output aprovado pelos guardrails.",
  };
}

export function validateQueryResponse(
  response: unknown,
): QueryResponseValidationResult {
  const structuredOutput = validateStructuredOutput(response);

  if (!structuredOutput.isValid || structuredOutput.payload === null) {
    return {
      status: "rejected",
      payload: buildFallbackPayload(structuredOutput.reason),
      reason: structuredOutput.reason,
    };
  }

  return applyGuardrails(structuredOutput.payload);
}
```

**Notas de design (fail-safe):**
- Quando uma clausula menciona carga perigosa + devolução mas **não há nem afirmação nem negação clara** (frase ambígua), o comportamento continua sendo **bloquear** (`!hasClearDenial` = `true` nesse caso) — mesma postura fail-safe do código original, agora aplicada com detecção mais ampla.
- `affirmsDangerousReturn` é avaliado por cláusula (frase), não no texto inteiro, eliminando o vazamento de contexto entre frases não relacionadas.
- Nenhuma função pública mudou de nome ou assinatura (`validateStructuredOutput`, `applyGuardrails`, `validateQueryResponse`, mensagens exportadas).

---

## Seção 3: Testes adicionados/ajustados (Vitest)

Adicionar ao arquivo existente `tests/unit/response-validator.test.ts` (os testes já existentes continuam passando sem alteração):

```ts
describe("response-validator: schema hardening", () => {
  it("rejects payloads with unexpected extra fields (strict object)", () => {
    const result = validateStructuredOutput({
      answer: "Resposta valida.",
      source_document: "doc.md",
      confidence_score: 0.5,
      unexpected_field: "nao deveria existir",
    });

    expect(result.isValid).toBe(false);
    expect(result.payload).toBeNull();
    expect(result.reason).toBe(INVALID_SCHEMA_MESSAGE);
  });

  it("rejects confidence_score above 1", () => {
    const result = validateStructuredOutput({
      answer: "Resposta valida.",
      source_document: "doc.md",
      confidence_score: 1.5,
    });

    expect(result.isValid).toBe(false);
    expect(result.reason).toBe(INVALID_SCHEMA_MESSAGE);
  });

  it("rejects confidence_score below 0", () => {
    const result = validateStructuredOutput({
      answer: "Resposta valida.",
      source_document: "doc.md",
      confidence_score: -0.01,
    });

    expect(result.isValid).toBe(false);
    expect(result.reason).toBe(INVALID_SCHEMA_MESSAGE);
  });

  it("rejects confidence_score of a non-numeric type", () => {
    const result = validateStructuredOutput({
      answer: "Resposta valida.",
      source_document: "doc.md",
      confidence_score: "0.9" as unknown as number,
    });

    expect(result.isValid).toBe(false);
    expect(result.reason).toBe(INVALID_SCHEMA_MESSAGE);
  });

  it("treats an empty source_document as missing at the structured-output layer", () => {
    const result = validateStructuredOutput({
      answer: "Resposta sem fonte real.",
      source_document: "",
      confidence_score: 0.5,
    });

    expect(result.isValid).toBe(false);
    expect(result.payload).toBeNull();
    expect(result.reason).toBe(MISSING_SOURCE_DOCUMENT_MESSAGE);
  });

  it("treats a whitespace-only source_document as missing at the structured-output layer", () => {
    const result = validateStructuredOutput({
      answer: "Resposta sem fonte real.",
      source_document: "   ",
      confidence_score: 0.5,
    });

    expect(result.isValid).toBe(false);
    expect(result.payload).toBeNull();
    expect(result.reason).toBe(MISSING_SOURCE_DOCUMENT_MESSAGE);
  });

  it("rejects null and undefined source_document", () => {
    const nullResult = validateStructuredOutput({
      answer: "Resposta.",
      source_document: null,
      confidence_score: 0.5,
    });
    const undefinedResult = validateStructuredOutput({
      answer: "Resposta.",
      confidence_score: 0.5,
    });

    expect(nullResult.isValid).toBe(false);
    expect(nullResult.reason).toBe(MISSING_SOURCE_DOCUMENT_MESSAGE);
    expect(undefinedResult.isValid).toBe(false);
    expect(undefinedResult.reason).toBe(MISSING_SOURCE_DOCUMENT_MESSAGE);
  });
});

describe("response-validator: dangerous cargo return detection - false negatives", () => {
  it("blocks a verb-form phrasing not covered by the old noun-only regex", () => {
    const result = validateQueryResponse({
      answer: "Voce pode devolver a carga perigosa sem problema.",
      source_document: "politica-operacional.md",
      confidence_score: 0.7,
    });

    expect(result.status).toBe("blocked");
    expect(result.reason).toBe(DANGEROUS_RETURN_BLOCK_MESSAGE);
  });

  it("blocks plural phrasing of dangerous cargo", () => {
    const result = validateQueryResponse({
      answer: "As cargas perigosas podem ser devolvidas normalmente.",
      source_document: "politica-operacional.md",
      confidence_score: 0.7,
    });

    expect(result.status).toBe("blocked");
  });

  it("blocks a synonym for dangerous cargo (material toxico)", () => {
    const result = validateQueryResponse({
      answer: "E permitido devolver material toxico ao fornecedor.",
      source_document: "politica-operacional.md",
      confidence_score: 0.7,
    });

    expect(result.status).toBe("blocked");
  });

  it("blocks a double-negative that in fact affirms permission", () => {
    const result = validateQueryResponse({
      answer: "Nao ha impedimento para a devolucao de carga perigosa.",
      source_document: "politica-operacional.md",
      confidence_score: 0.7,
    });

    expect(result.status).toBe("blocked");
  });
});

describe("response-validator: dangerous cargo return detection - false positives", () => {
  it("accepts a proper denial phrased with negation next to the permission word", () => {
    const result = validateQueryResponse({
      answer: "A devolucao de carga perigosa nao e permitida pela politica interna.",
      source_document: "politica-operacional.md",
      confidence_score: 0.7,
    });

    expect(result.status).toBe("accepted");
  });

  it("does not leak an unrelated permission statement from another sentence", () => {
    const result = validateQueryResponse({
      answer:
        "Nao temos registro de devolucao de carga perigosa neste mes. O acesso ao patio e permitido apenas para motoristas cadastrados.",
      source_document: "politica-operacional.md",
      confidence_score: 0.7,
    });

    expect(result.status).toBe("accepted");
  });
});
```

---

## Seção 4: Resumo das mudanças

- **Schema (`response-builder.ts`):** `confidence_score` agora exige `min(0).max(1)`; `source_document` agora usa `.trim().min(1)`, então vazio/whitespace já falha na validação de schema (defesa em profundidade, além da checagem que já existia em `applyGuardrails`). O objeto já era `.strict()` — confirmado e coberto por teste.
- **Detecção de risco (`response-validator.ts`):** os regexes de "carga perigosa" e "devolução" foram ampliados para cobrir plural, sinônimos (material/produto/mercadoria x perigoso/tóxico/inflamável/explosivo/radioativo/corrosivo) e formas verbais (devolver/devolvida/devolvendo), com normalização de acentuação.
- **Lógica de bloqueio:** a avaliação passou a ser por cláusula/frase (em vez de regex `.*` sem limite sobre o texto todo), e agora é negation-aware (`NEGATED_PERMISSION_PATTERN`), corrigindo um falso positivo em que uma negação correta ("não é permitida") era tratada como afirmação, e também corrigindo o vazamento de contexto entre frases não relacionadas. Um duplo-negativo comum ("não há impedimento") passou a ser tratado corretamente como afirmação (evitando um bypass).
- Nenhuma função pública, assinatura ou mensagem exportada foi removida ou renomeada; todos os testes originais continuam válidos.
