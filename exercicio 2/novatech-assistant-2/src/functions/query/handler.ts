export interface QueryHandlerInput {
  body: unknown;
}

export interface QueryHandlerOutput {
  status: number;
  body: unknown;
}

export async function queryHandler(
  _input: QueryHandlerInput,
): Promise<QueryHandlerOutput> {
  throw new Error("queryHandler not implemented.");
}
