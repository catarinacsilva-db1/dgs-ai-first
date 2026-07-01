import { z } from "zod";

export const queryRequestSchema = z.object({
  pergunta: z.string().trim().min(1, "O campo 'pergunta' nao pode ser vazio."),
});

export type QueryRequestInput = z.infer<typeof queryRequestSchema>;

export function validateQueryRequest(input: unknown): QueryRequestInput {
  return queryRequestSchema.parse(input);
}
