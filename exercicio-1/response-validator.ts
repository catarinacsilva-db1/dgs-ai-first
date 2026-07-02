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

const NEGATIVE_LANGUAGE_PATTERN =
  /\b(n[ãa]o|nunca|jamais|imposs[ií]vel|proibid[ao]?|vedad[ao]?)\b/i;
const DANGEROUS_CARGO_PATTERN = /carga perigosa/i;
const RETURN_PATTERN = /devolu[cç][ãa]o/i;
const POSITIVE_RETURN_PATTERN =
  /(devolu[cç][ãa]o).*(pode|poss[ií]vel|permitid[ao]?|autorizad[ao]?)|(pode|poss[ií]vel|permitid[ao]?|autorizad[ao]?).*(devolu[cç][ãa]o)/i;

function buildFallbackPayload(message: string): QueryResponsePayload {
  return {
    answer: message,
    source_document: "N/A",
    confidence_score: 0,
  };
}

function mentionsDangerousReturnScenario(answer: string): boolean {
  return DANGEROUS_CARGO_PATTERN.test(answer) && RETURN_PATTERN.test(answer);
}

function affirmsDangerousReturn(answer: string): boolean {
  return mentionsDangerousReturnScenario(answer)
    && POSITIVE_RETURN_PATTERN.test(answer);
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
      || !NEGATIVE_LANGUAGE_PATTERN.test(payload.answer))
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
