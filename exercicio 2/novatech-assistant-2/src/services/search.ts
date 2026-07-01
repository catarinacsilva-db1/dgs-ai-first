export type EmbeddingVector = number[];

export interface SearchChunk {
  id: string;
  content: string;
  score: number;
}

export async function generateEmbedding(
  _question: string,
): Promise<EmbeddingVector> {
  throw new Error("generateEmbedding not implemented.");
}

export async function searchTopChunks(
  _embedding: EmbeddingVector,
): Promise<SearchChunk[]> {
  throw new Error("searchTopChunks not implemented.");
}
