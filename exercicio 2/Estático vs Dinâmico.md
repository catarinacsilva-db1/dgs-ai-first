# Anatomia Completa do Contexto — Estático vs Dinâmico

## Partes Estáticas
*(presentes em toda query — nunca mudam)*

| Seção | Estimativa de Tokens | Base do cálculo |
|---|---|---|
| IDENTIDADE | ~95 tokens | ~70 palavras × 1,35 |
| REGRAS R1–R5 | ~280 tokens | ~210 palavras × 1,35 |
| ORDEM DE PRIORIDADE | ~95 tokens | ~70 palavras × 1,35 |
| INSTRUÇÕES PARA CHUNKS | ~135 tokens | ~100 palavras × 1,35 |
| FORMATO DE RESPOSTA | ~110 tokens | ~80 palavras × 1,35 |
| **Total estático** | **~825 tokens** | |

> Regra usada: português tem ~1,35 tokens/palavra (mais que inglês pela morfologia)

---

## Partes Dinâmicas
*(mudam a cada query)*

| Seção | Estimativa de Tokens | Observação |
|---|---|---|
| `{{CHUNKS_RECUPERADOS}}` | ~500–2.500 tokens | 500 tokens × 1 a 5 chunks recuperados |
| `{{TIER_DO_CLIENTE}}` | ~5–15 tokens | Ausente ou 1-2 palavras ("Gold", "não informado") |
| `{{PERGUNTA}}` | ~20–60 tokens | Pergunta típica de atendente: 15–45 palavras |
| `{{ASSUNTO_PERGUNTADO}}` | ~10–30 tokens | Nome do tema ou assunto perguntado |
| `{{NOME_EQUIPE_RESPONSÁVEL}}` | ~5–20 tokens | Nome da equipe responsável pelo arquivo|
| **Total dinâmico (típico)** | **~1.500–5.000 tokens** | |

---

## Orçamento de Contexto Total (GPT-4o — 128K tokens)
Janela total disponível:          128.000 tokens
(-) Estático (system prompt):      -  825 tokens
(-) Chunks recuperados (5×500):   -2.500 tokens
(-) Pergunta + tier:               -   75 tokens
                                  ─────────────
Margem disponível p/ resposta:   ~122.100 tokens