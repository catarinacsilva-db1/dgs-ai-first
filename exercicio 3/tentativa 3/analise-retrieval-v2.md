# Análise de Retrieval — Pipeline RAG NovaTech (v2)

**Data:** 2026-06-19  
**Execução:** Pós-reindexação com `MarkdownHeaderTextSplitter`, threshold 0.35, métrica cosine explícita  
**Referência:** Anexo B — Mapa de cobertura

---

## Resultado por pergunta

### P1 — "Qual o prazo de devolução?"

**Gabarito Anexo B:** POL-001-A *(obrigatório)*, POL-001-B *(obrigatório)*, POL-001-C *(opcional)*

| # | Fonte | Seção recuperada | Score | Gabarito | Veredito |
|---|-------|-----------------|-------|----------|----------|
| 1 | POL-001-politica-devolucao.md | 3.5 Custos de devolução | 0.63 | POL-001-D (opcional) | Aceito |
| 2 | POL-001-politica-devolucao.md | 3.1 Prazo geral | 0.58 | **POL-001-A (obrigatório)** | ✅ Correto |
| 3 | POL-001-politica-devolucao.md | 3.3 Procedimento | 0.56 | POL-001-C (opcional) | ✅ Aceito |
| 4 | FAQ-atendimento.md | Item 3 — devolução perigosa | 0.55 | Não previsto para P1 | Ruído |
| 5 | PROC-042-frete-especial-v1.md | Seção 3 — prazo frete especial | 0.55 | Não previsto | Ruído + versão anterior |

**Obrigatórios:** POL-001-A ✅ | POL-001-B ❌ (seção 3.2 ausente)  
**Opcionais:** POL-001-C ✅  
**Taxa de obrigatórios:** 1/2 (50%)

**Análise:** Melhora em relação à v1 (que recuperava 3.5 e 3.1). Agora 3.3 (procedimento) também aparece como opcional. O chunk POL-001-B (seção 3.2 — exceções ANTT) continua ausente — provavelmente dividido em dois pelo fallback de 800 chars, e a primeira metade (com a lista de classes ANTT) não atingiu score suficiente. PROC-042-v1 seção 3 como ruído indica que frete especial e devolução têm sobreposição semântica residual.

---

### P2 — "Posso devolver carga perigosa?"

**Gabarito Anexo B:** POL-001-B *(obrigatório)*, FAQ-03 *(opcional)*, POL-001-A *(opcional)*

| # | Fonte | Seção recuperada | Score | Gabarito | Veredito |
|---|-------|-----------------|-------|----------|----------|
| 1 | FAQ-atendimento.md | Item 3 — devolução perigosa | 0.60 | FAQ-03 (opcional) | ✅ Aceito |
| 2 | FAQ-atendimento.md | Item 22 — seguro de carga | 0.58 | Não previsto | Ruído |
| 3 | POL-001-politica-devolucao.md | Final da seção 3.2 (lacre + ramal 4500) | 0.57 | **POL-001-B (obrigatório)** | ⚠️ Parcial |
| 4 | FAQ-atendimento.md | Item 38 — carga danificada | 0.55 | Não previsto | Ruído |
| 5 | FAQ-atendimento.md | Item 32 — perigosa + expresso | 0.52 | Não previsto | Ruído |

**Obrigatórios:** POL-001-B ⚠️ (fragmento parcial — apenas final da seção, sem lista ANTT)  
**Opcionais:** FAQ-03 ✅  
**Taxa de obrigatórios:** 0/1 (0%) — o fragmento recuperado está incompleto

**Análise:** Documento [3] contém apenas o final da seção 3.2: *"Cargas com lacre de segurança violado... ramal 4500"*. A parte crítica (lista ANTT classes 1–6, que define quais cargas são não-elegíveis) não foi recuperada — está em outro chunk gerado pelo fallback splitter. O LLM tem acesso ao ramal 4500 mas não à fundamentação legal (resolução ANTT nº 5.947/2021). FAQ-22 e FAQ-38 continuam como ruído mesmo com threshold 0.35, indicando que a sobreposição semântica de "carga perigosa" puxa itens de domínios diferentes.

---

### P3 — "Qual o SLA do cliente Gold?"

**Gabarito Anexo B:** SLA-2024-B *(obrigatório)*, SLA-2024-A *(opcional)*, SLA-2024-C *(opcional)*

| # | Fonte | Seção recuperada | Score | Gabarito | Veredito |
|---|-------|-----------------|-------|----------|----------|
| 1 | SLA-2024-tabela-sla-clientes.md | Seção 5 — Medição e reportes | 0.55 | Não previsto | Ruído contextual |
| 2 | FAQ-atendimento.md | Item 41 — resposta vs resolução de SLA | 0.55 | Não previsto (conteúdo equivalente a SLA-2024-B) | Útil, mas fonte informal |
| 3 | FAQ-atendimento.md | Item 15 — tier Platinum | 0.54 | Opcional para outra query | Ruído |
| 4 | SLA-2024-tabela-sla-clientes.md | Seção 1 — Classificação de clientes | 0.51 | SLA-2024-A (opcional) | ✅ Aceito |
| 5 | SLA-2024-tabela-sla-clientes.md | Título/metadados do documento (#) | 0.47 | Não previsto | Chunk de cabeçalho (baixo valor) |

**Obrigatórios:** SLA-2024-B ❌ (tabela de SLAs por tier não recuperada)  
**Opcionais:** SLA-2024-A ✅  
**Taxa de obrigatórios:** 0/1 (0%)

**Análise:** Melhora estrutural significativa — SLA-2024 agora é recuperado (antes retornava `[SEM CONTEXTO]`). A redução do threshold de 0.40 para 0.35 resolveu a falha total. Porém SLA-2024-B (seção 2 — tabela com Gold: 2h/24h) ainda não aparece. O FAQ-41 compensa parcialmente: contém *"O Gold tem 2h de resposta e 24h de resolução. Silver é 4h e 48h. Standard é 8h e 72h"* — a informação correta, mas em fonte informal sem respaldo contratual. Chunk 5 (título `#`) é ruído estrutural — captura o bloco de metadados do documento, útil para rastreabilidade mas não para resposta.

**Comportamento esperado do LLM:** Responderá corretamente com os SLAs (via FAQ-41 e parcialmente via SLA-2024-A), mas usando fonte informal. O sistema deveria priorizar SLA-2024-B para conformidade contratual.

---

### P4 — "Frete para 600kg para Manaus?"

**Gabarito Anexo B:** PROC-042v2-B *(obrigatório)*, PROC-042v2-A *(obrigatório)*, PROC-042-B *(opcional — risco de contradição)*

| # | Fonte | Seção recuperada | Score | Gabarito | Veredito |
|---|-------|-----------------|-------|----------|----------|
| 1 | PROC-042-frete-especial-v1.md | Seção 1 — Objetivo | 0.47 | Não previsto | Ruído + versão anterior |
| 2 | PROC-042-v2-frete-especial-revisado.md | Seção 4 — Condições especiais | 0.47 | PROC-042v2-D (não obrigatório) | Parcialmente relevante |
| 3 | PROC-042-v2-frete-especial-revisado.md | Seção 1 — Objetivo | 0.46 | Não previsto | Baixo valor |
| 4 | PROC-042-v2-frete-especial-revisado.md | Seção 2 — Fórmula de cálculo | 0.46 | **PROC-042v2-A (obrigatório)** | ✅ Correto |
| 5 | PROC-042-frete-especial-v1.md | Seção 2 — Fórmula (v1) | 0.46 | PROC-042-A (versão antiga) | Ruído + versão anterior |

**Obrigatórios:** PROC-042v2-A ✅ (fórmula de cálculo) | PROC-042v2-B ❌ (multiplicadores regionais — seção 2.1 ausente)  
**Taxa de obrigatórios:** 1/2 (50%)

**Análise:** Melhora relevante — PROC-042-v2 agora é recuperado, com fórmula de cálculo presente. Porém o chunk crítico PROC-042v2-B (seção 2.1 — tabela de multiplicadores regionais, onde Norte = 1.8) continua ausente. O enriquecimento geográfico com nomes de cidades não produziu efeito visível — o chunk de multiplicadores (subsecao "2.1") não aparece nem nos 5 resultados, sugerindo que seu score está abaixo de 0.35 mesmo com enriquecimento. O gap semântico "Manaus" → "Norte" persiste como a limitação mais resistente do pipeline. Versões v1 marcadas corretamente com `[VERSÃO ANTERIOR]` — o mecanismo de sinalização está funcionando.

---

### P5 — "Carga perigosa com frete expresso?"

**Gabarito Anexo B:** FAQ-32 *(obrigatório)*

| # | Fonte | Seção recuperada | Score | Gabarito | Veredito |
|---|-------|-----------------|-------|----------|----------|
| 1 | FAQ-atendimento.md | Item 32 — perigosa + expresso | 0.69 | **FAQ-32 (obrigatório)** | ✅ Correto |
| 2 | FAQ-atendimento.md | Item 38 — carga danificada | 0.60 | Não previsto | Ruído |
| 3 | FAQ-atendimento.md | Item 22 — seguro de carga | 0.59 | Não previsto | Ruído |
| 4 | FAQ-atendimento.md | Item 3 — devolução perigosa | 0.55 | Não previsto | Ruído |
| 5 | POL-001-politica-devolucao.md | Final seção 3.2 (lacre + ramal 4500) | 0.54 | Não previsto | Ruído |

**Obrigatórios:** FAQ-32 ✅  
**Taxa de obrigatórios:** 1/1 (100%)

**Análise:** Chunk correto recuperado com score alto (0.69). Porém 4 dos 5 chunks são ruído — threshold 0.35 é mais permissivo que 0.40 e deixa entrar mais itens de FAQ tangencialmente relacionados a "carga perigosa". O LLM verá o contexto correto (FAQ-32) mas com informações de outros domínios no mesmo prompt. Risco baixo de resposta errada dado o score dominante de 0.69 do chunk correto.

---

## Comparativo v1 → v2

| Pergunta | Obrigatórios gabarito | v1 (threshold 0.40) | v2 (threshold 0.35) | Evolução |
|---|---|---|---|---|
| P1 — Prazo de devolução | POL-001-A, POL-001-B | 1/2 (50%) | 1/2 (50%) | = |
| P2 — Carga perigosa devolução | POL-001-B | 0/1 (0%) | 0/1 — fragmento parcial ⚠️ | ↑ parcial |
| P3 — SLA Gold | SLA-2024-B | 0/1 (0%) — SEM CONTEXTO | 0/1 (0%) — SLA-2024 recuperado | ↑ estrutural |
| P4 — Frete Manaus | PROC-042v2-B, PROC-042v2-A | 0/2 (0%) — SEM CONTEXTO | 1/2 (50%) | ↑↑ |
| P5 — Perigosa + expresso | FAQ-32 | 1/1 (100%) | 1/1 (100%) | = |
| **Total** | **7 obrigatórios** | **2/7 (29%)** | **3/7 (43%)** | **↑ +14pp** |

---

## Padrões identificados

### O que funcionou
- **Redução do threshold (0.40 → 0.35):** resolveu a falha total em P3 e P4. SLA-2024 e PROC-042-v2 agora aparecem nos resultados.
- **Chunking estrutural por headers:** P1 recupera 3.1 + 3.3 + 3.5 de forma coerente (antes misturava seções). Estrutura de seções preservada.
- **Sinalização `is_latest`:** PROC-042-v1 chunks em P4 corretamente marcados com `[VERSÃO ANTERIOR]`.
- **Captura do cabeçalho `#`:** Chunk de metadados do SLA-2024 aparece em P3 — confirma que o bloco pré-`##` agora é indexado.

### Problemas remanescentes

**1. Seção 3.2 (POL-001-B) dividida pelo fallback splitter**  
A seção de exceções ANTT é longa o suficiente para acionar o fallback de 800 chars, gerando dois sub-chunks. O sub-chunk recuperado em P2 e P5 é sempre a segunda metade (lacre + ramal 4500), nunca a primeira (classes ANTT 1–6). A primeira metade tem score mais baixo para queries sobre "carga perigosa" — paradoxalmente, o conteúdo mais relevante tem embedding menos discriminativo.

**2. Seção 2.1 da PROC-042v2 (multiplicadores regionais) não recuperada**  
O enriquecimento geográfico não produziu efeito detectável. PROC-042v2-B (Norte = 1.8 + lista de cidades) não aparece nos top-5 para "Frete para 600kg para Manaus?". Score do chunk de multiplicadores provavelmente abaixo de 0.35 mesmo com o enriquecimento — limitação do modelo `all-MiniLM-L6-v2` que não conecta semanticamente "Manaus" a "Norte" mesmo com as cidades presentes.

**3. SLA-2024-B (tabela de SLAs) não recuperada**  
A seção 2 do SLA-2024 com os tempos de resposta/resolução por tier não aparece para P3. FAQ-41 compensa com informação equivalente, mas é fonte informal. Scores da seção 2 provavelmente ficam entre 0.35–0.45 mas abaixo da seção 5 (medição) e seção 1 (classificação).

**4. Aumento de ruído com threshold 0.35**  
P5 passou de 2 chunks de ruído (v1) para 4 (v2). FAQ-22, FAQ-38, FAQ-03 e POL-001 fragmento todos entram com scores entre 0.52–0.60. O threshold mais permissivo resolve falhas de cobertura (P3, P4) mas aumenta o ruído em perguntas bem cobertas (P5).

---

## Causa-raiz remanescente

O problema central não resolvido é o modelo de embedding `all-MiniLM-L6-v2`:
- Treinado em inglês — baixa discriminação semântica para documentos em português
- Scores uniformemente comprimidos (0.45–0.65) — pequena margem entre chunks relevantes e irrelevantes
- Gap geográfico cidade/região não resolvido pelo enriquecimento textual

A troca para `paraphrase-multilingual-MiniLM-L12-v2` é a correção definitiva. Requer:
1. Atualizar `model_name` em `indexar_documentos.py` e `pipe-rag.py`
2. Reindexação completa com `forcar_reindex=s`
3. Reavaliação do threshold (modelo multilíngue provavelmente permite threshold mais alto, 0.50+)
