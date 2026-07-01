import type { QueryResponsePayload } from "../functions/query/response-builder";

export function validateQueryResponse(
  _response: unknown,
): QueryResponsePayload {
  throw new Error("validateQueryResponse not implemented.");
}
