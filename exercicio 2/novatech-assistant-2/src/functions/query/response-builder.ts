export interface QueryResponsePayload {
  resposta: string;
  source_document: string[];
}

export function buildQueryResponse(
  _payload: QueryResponsePayload,
): QueryResponsePayload {
  throw new Error("buildQueryResponse not implemented.");
}
