import type { SearchChunk } from "./search";

export interface PromptBuildInput {
  question: string;
  chunks: SearchChunk[];
  systemPrompt: string;
}

export function resolveChunksByValidity(
  _chunks: SearchChunk[],
): SearchChunk[] {
  throw new Error("resolveChunksByValidity not implemented.");
}

export function truncateChunksByBudget(
  _chunks: SearchChunk[],
  _maxTokens: number,
): SearchChunk[] {
  throw new Error("truncateChunksByBudget not implemented.");
}

export function buildPrompt(_input: PromptBuildInput): string {
  throw new Error("buildPrompt not implemented.");
}
