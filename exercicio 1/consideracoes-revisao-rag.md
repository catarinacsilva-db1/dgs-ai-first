# Considerações Pós-Revisão — Pipeline RAG
`v1.0 | Junho 2026 | Síntese da revisão crítica de analise-tecnica-rag-pipeline.md`

---

## 1. Principais Problemas Identificados

| # | Problema | Severidade | Componente |
|---|---|---|---|
| P1 | Fator de tokenização incorreto para PT técnico (0,72 vs 0,60–0,65 real) | **Crítico** | Todas as estimativas |
| P2 | Overhead de contextualização/chunk subestimado (8% vs 30–45% real) | **Crítico** | Tamanho do índice |
| P3 | Planilhas de frete por CEP podem ser 10–30× o estimado | **Crítico** | Infraestrutura e custo |
| P4 | Posicionamento "espiral" quebra documentos procedimentais sequenciais | **Alto** | Qualidade de respostas |
| P5 | `doc_family_id` assumido resolvido — algoritmo não especificado | **Alto** | Grafo de versões |
| P6 | Mecanismo de escalada entre camadas de chunking não definido | **Alto** | Arquitetura |
| P7 | Ausência de evaluation framework e métricas-alvo | **Alto** | Validação |
| P8 | Hierarquia de confiança entre fontes conflitantes ausente do prompt | **Alto** | Geração |

---

## 2. Ajustes de Estimativas

### Tokenização e Tamanho da Base

| Parâmetro | Original | Revisado | Δ |
|---|---|---|---|
| Fator PT (palavras/token) | 0,72 | 0,60–0,65 | +10–20% em tokens |
| Overhead wiki | 15% | 35–42% | +~230K tokens |
| Overhead tabelas serializadas | 25–30% | 40–55% | +~200K tokens |
| **Total — cenário mediano** | **5,3M tokens** | **6,2–7,0M tokens** | **+17–32%** |
| **Total — cenário pessimista** | **7,5M tokens** | **10M–30M tokens*** | Indeterminado |

\* Depende do conteúdo real das planilhas. Requer inventário amostral antes de qualquer estimativa.

### Chunks e Budget de Contexto

| Parâmetro | Original | Revisado |
|---|---|---|
| Chunks teóricos no contexto | 248 | ~220 (chunk efetivo ~375 tokens c/ prefixo) |
| Chunks operacionais recomendados | 10–20 | **10–15** (maior rigor contra LitM) |
| Total chunks no índice | Não calculado | **~62.000 mínimo** (L1 + L2) |
| RAM para vetores (text-emb-3-large) | Não calculado | **~745 MB mínimo** |
| Precisão Tesseract (docs limpos, PT) | ~97% | **89–94%** |

---

## 3. Riscos Priorizados

| Risco | Impacto | Prob. | Prioridade |
|---|---|---|---|
| Planilhas inflam índice 10–30× | Alto | Alta | 🔴 P0 |
| Sem evaluation framework — validação impossível | Alto | Certa | 🔴 P0 |
| Conflito FAQ × PROC sem hierarquia de confiança no prompt | Alto | Certa | 🔴 P0 |
| Semantic drift invalida índice ao trocar modelo de embedding | Alto | Alta | 🔴 P0 |
| `doc_family_id` indetectável para nomes inconsistentes | Alto | Alta | 🟠 P1 |
| Overhead real de contextualização estoura RAM e custo | Médio | Alta | 🟠 P1 |
| Posicionamento espiral degrada respostas procedimentais | Médio | Alta | 🟠 P1 |
| Histórico multi-turn sem política de truncagem | Médio | Média | 🟡 P2 |
| Re-embedding sem versionamento → inconsistência silenciosa | Alto | Baixa | 🟡 P2 |

---

## 4. Itens de Ação

### Pré-ingestão (bloqueantes)
- [ ] Tokenizar 10 docs por tipo com `tiktoken` (cl100k_base) — calcular fator empírico real
- [ ] Inventariar 5 planilhas representativas e contar células ativas — **não iniciar ingestão sem isso**
- [ ] Adicionar hierarquia de confiança ao system prompt: `POL > PROC (vigente) > SLA > FAQ`
- [ ] Especificar algoritmo de `doc_family_id`: prefixo normalizado + clustering semântico de títulos

### Arquitetura e pipeline
- [ ] Adicionar `embedding_model_version` aos metadados de cada chunk
- [ ] Substituir posicionamento espiral: `factual → espiral | procedural → ordem documental | comparative → intercalado por fonte`
- [ ] Definir critério de escalada L2→L3 (threshold do reranker) e desempate OCR para valores numéricos
- [ ] Adicionar política de truncagem de histórico multi-turn antes do retrieval

### Validação (bloqueante para produção)
- [ ] Criar 150 pares Q&A de avaliação: 50 factual / 30 procedural / 25 versionamento / 25 gaps / 20 conflitos
- [ ] Definir métricas-alvo: **Recall@10 ≥ 0,85 | MRR ≥ 0,70 | Faithfulness ≥ 0,80**
- [ ] Benchmarkar chunking hierárquico vs. chunking fixo 512t — não assumir superioridade sem dados

---

## 5. Decisões Pendentes

| Questão | Como resolver |
|---|---|
| Planilhas de frete por CEP: indexar tudo ou usar tool call para lookup? | Prototipar ambas; medir latência e custo por query |
| `text-embedding-3-large` vs `multilingual-e5-large` para português | Testar no dataset de avaliação com queries reais |
| CPU (150–400ms) vs GPU (10–50ms) para reranking | Definir SLA de latência antes de escolher infra |
| Threshold OCR para geração de Layer 1 | Testar 0,70 / 0,80 / 0,90 no corpus amostrado |

---

*Próxima ação imediata: inventário de planilhas + tokenização empírica — ambos bloqueiam todas as estimativas de infraestrutura.*
