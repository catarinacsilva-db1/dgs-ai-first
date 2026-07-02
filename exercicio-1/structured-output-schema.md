# Schema Zod do Structured Output

```ts
import { z } from "zod";

export const queryResponseSchema = z
  .object({
    answer: z.string(),
    source_document: z.string(),
    confidence_score: z.number().finite(),
  })
  .strict();
```

## Campos

- `answer`: texto principal da resposta.
- `source_document`: identificador do documento-fonte usado na resposta.
- `confidence_score`: score numérico finito de confiança.