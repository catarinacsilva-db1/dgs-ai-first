export interface CompletionInput {
  prompt: string;
}

export interface CompletionOutput {
  text: string;
}

export async function requestCompletion(
  _input: CompletionInput,
): Promise<CompletionOutput> {
  throw new Error("requestCompletion not implemented.");
}
