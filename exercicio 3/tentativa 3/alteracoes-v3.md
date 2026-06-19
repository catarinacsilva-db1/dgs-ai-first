# Alterações v3 — Pipeline RAG NovaTech

**Data:** 2026-06-19  
**Base:** Análise `analise-retrieval-v2.md` + leitura estrutural do Anexo A  
**Taxa anterior:** 3/7 chunks obrigatórios (43%)  
**Gaps corrigidos:** POL-001-B truncada · SLA-2024-B não recuperada · PROC-042v2-B fora do top-5

---

## 1. `indexar_documentos.py` — Nova função `enriquecer_tabelas`

### Problema

Tabelas markdown têm embedding fraco em modelos de linguagem, especialmente ingleses. O formato `| col | val |` não tem representação semântica equivalente ao texto narrativo. Efeito direto:

- **SLA-2024-B** (seção 2 — tabela com Gold/Silver/Standard) perdia para seção 5 (texto corrido sobre Azure DevOps) e FAQ-41 (narrativa "Gold tem 2h de resposta") na busca por "Qual o SLA do cliente Gold?"
- **PROC-042v2-B** (seção 2.1 — tabela de multiplicadores regionais) tinha sinal semântico fraco para "Frete para Manaus?" mesmo com enriquecimento geográfico

### Correção

Nova função `enriquecer_tabelas(texto)` adicionada após `enriquecer_geograficamente`.

**Antes:** não existia.

**Depois:**
```python
def enriquecer_tabelas(texto: str) -> str:
    if texto.count("|") < 4:
        return texto

    cabecalho = None
    rows_texto = []
    separador_visto = False

    for linha in texto.split("\n"):
        stripped = linha.strip()
        if not stripped or "|" not in stripped:
            continue
        if re.match(r"^\|[\s\-:]+(\|[\s\-:]+)*\|?$", stripped):
            separador_visto = True
            continue
        celulas = [c.strip() for c in stripped.strip("|").split("|")]
        celulas = [c for c in celulas if c]
        if len(celulas) < 2:
            continue
        if cabecalho is None:
            cabecalho = celulas
            continue
        if separador_visto and len(celulas) >= len(cabecalho):
            partes = [f"{cabecalho[i]}: {celulas[i]}" for i in range(1, len(cabecalho))]
            rows_texto.append(f"{celulas[0]} — " + ", ".join(partes))

    if not rows_texto:
        return texto

    return texto + "\n\nResumo textual da tabela:\n" + "\n".join(rows_texto)
```

**Lógica:** detecta a primeira tabela markdown (aguarda a linha separadora `|---|---|` para confirmar que é uma tabela real, não texto com pipes), converte cada linha em texto narrativo e acrescenta ao final do chunk.

**Resultado para SLA-2024-B:**
```
Resumo textual da tabela:
Tempo de primeira resposta (chamados gerais) — Gold: Até 2h úteis, Silver: Até 4h úteis, Standard: Até 8h úteis
Tempo de resolução (chamados gerais) — Gold: Até 24h úteis, Silver: Até 48h úteis, Standard: Até 72h úteis
Tempo de primeira resposta (incidentes críticos) — Gold: Até 30min, Silver: Até 1h, Standard: Até 2h
Tempo de resolução (incidentes críticos) — Gold: Até 4h, Silver: Até 8h, Standard: Até 24h
Disponibilidade do portal de tracking — Gold: 99,5%, Silver: 99,0%, Standard: 98,0%
Gerente de conta dedicado — Gold: Sim, Silver: Não, Standard: Não
Relatório mensal de performance — Gold: Sim (detalhado), Silver: Sim (resumido), Standard: Sob demanda
```

**Resultado para PROC-042v2-B** (combinado com enriquecimento geográfico):
```
Resumo textual da tabela:
Sul — Multiplicador: 1.3
Sudeste — Multiplicador: 1.1
Centro-Oeste — Multiplicador: 1.4
Nordeste — Multiplicador: 1.5
Norte — Multiplicador: 1.8

Cidades atendidas por região:
- Norte: Manaus, Belém, Porto Velho, Macapá, Boa Vista, Rio Branco, Palmas
...
```

**Aplicação:** chamada em `chunkar_por_headers` para todos os chunks, logo após o enriquecimento geográfico:

```python
# Enriquecimento geográfico: apenas em chunks de PROC-042 com tabela regional
if "PROC-042" in doc_meta["source"]:
    text = enriquecer_geograficamente(text)

# Enriquecimento de tabelas: converte markdown table para texto narrativo
# Aplicado a todos os chunks — resolve embedding fraco de células | col | val |
text = enriquecer_tabelas(text)
```

---

## 2. `indexar_documentos.py` — Limite do fallback: 800 → 1200 chars

### Problema

A seção 3.2 da POL-001 ("Exceções ao prazo geral") tem ~865 caracteres — acima do limite de 800 do fallback. Ela era dividida em dois sub-chunks:

| Sub-chunk | Conteúdo | Problema |
|---|---|---|
| Parte 1 | Lista ANTT classes 1–6 (cargas perigosas) | Não recuperada para P2 |
| Parte 2 | Bullet lacre + ramal 4500 | Recuperada em P2 e P5, mas incompleta |

O LLM recebia apenas o ramal 4500 sem a fundamentação legal (resolução ANTT nº 5.947/2021 e as classes 1–6).

### Correção

**Antes:**
```python
fallback_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    ...
)
...
if len(text) <= 800:
    documents.append(Document(...))
```

**Depois:**
```python
fallback_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    ...
)
...
if len(text) <= 1200:
    documents.append(Document(...))
```

**Por que 1200:** A maior seção dos documentos NovaTech após enriquecimento é a SLA-2024-B (~600 chars base + ~560 chars de resumo textual = ~1160 chars). Todas as seções ficam dentro de 1200. O fallback só entra para casos realmente excepcionais (seções > 1200 após enriquecimento).

**Seção 3.2 após correção:** ~865 chars → < 1200 → chunk único e íntegro. O LLM receberá a lista completa de classes ANTT, os três bullets e o ramal 4500 no mesmo chunk.

### Simplificação do fallback

Com os enriquecimentos aplicados **antes** da checagem de tamanho, os sub-chunks gerados no fallback já herdam o texto enriquecido — não é necessário re-aplicar os enriquecimentos dentro do loop.

**Antes:**
```python
else:
    for j, sub in enumerate(fallback_splitter.split_text(text)):
        sub = sub.strip()
        if sub:
            # Enriquecimento aplicado também nos sub-chunks para cobrir tabelas cortadas
            if "PROC-042" in doc_meta["source"]:
                sub = enriquecer_geograficamente(sub)
            m = {**metadata, "secao": f"{section_label} (parte {j + 1})"}
            documents.append(Document(page_content=sub, metadata=m))
```

**Depois:**
```python
else:
    # Enrichments já foram aplicados ao texto completo antes do split
    for j, sub in enumerate(fallback_splitter.split_text(text)):
        sub = sub.strip()
        if sub:
            m = {**metadata, "secao": f"{section_label} (parte {j + 1})"}
            documents.append(Document(page_content=sub, metadata=m))
```

---

## 3. `retriever.py` — Candidatos: `n*2` → `n*3`

### Problema

Com `k=n*2=10`, o chunk PROC-042v2-B (seção 2.1 — multiplicadores regionais) provavelmente ficava nas posições 6–10 do ranking de candidatos, fora do corte dos top-5 retornados. Chunks de seções de "Objetivo" (baixo valor informativo) ocupavam as posições superiores por terem vocabulário de frete mais genérico.

### Correção

**Antes:**
```python
raw_results = vectorstore.similarity_search_with_relevance_scores(
    query=pergunta,
    k=n * 2,
    ...
)
```

**Depois:**
```python
raw_results = vectorstore.similarity_search_with_relevance_scores(
    query=pergunta,
    k=n * 3,
    ...
)
```

Com `n=5`, passa de 10 para 15 candidatos avaliados. O threshold de 0.35 filtra os irrelevantes — o impacto em latência é pequeno (15 vetores consultados no HNSW vs. 10), mas a cobertura aumenta para queries onde o chunk correto está na cauda do ranking.

---

## 4. `retriever.py` — Remoção do parâmetro `embedding_model`

### Problema

O parâmetro `embedding_model: HuggingFaceEmbeddings` foi mantido na assinatura após a remoção do `embed_query` em uma versão anterior. Tornou-se parâmetro não utilizado (warning S1172 do SonarQube).

### Correção

**Antes:**
```python
from typing import List, Dict, Optional, Any
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def buscar_chunks(
    pergunta: str,
    vectorstore: Chroma,
    embedding_model: HuggingFaceEmbeddings,
    ...
```

**Depois:**
```python
from langchain_chroma import Chroma

def buscar_chunks(
    pergunta: str,
    vectorstore: Chroma,
    ...
```

Imports `typing` e `HuggingFaceEmbeddings` também removidos — não são mais usados no módulo.

### Atualização em `pipe-rag.py`

O ponto de chamada foi ajustado para remover o argumento:

**Antes:**
```python
chunks_recuperados = buscar_chunks(
    pergunta=pergunta,
    vectorstore=vectorstore,
    embedding_model=embeddings,
    n=5,
    score_minimo=0.35
)
```

**Depois:**
```python
chunks_recuperados = buscar_chunks(
    pergunta=pergunta,
    vectorstore=vectorstore,
    n=5,
    score_minimo=0.35
)
```

---

## 5. Mapeamento gap → correção

| Gap identificado (Anexo B) | Causa raiz | Correção aplicada |
|---|---|---|
| POL-001-B ausente (P2) | Seção 3.2 ~865 chars → fallback cortava em 2 sub-chunks; parte com ANTT classes não recuperada | Limite fallback 800 → 1200 |
| SLA-2024-B ausente (P3) | Tabela markdown com embedding fraco; FAQ-41 narrativo pontuava mais alto | `enriquecer_tabelas` em todos os chunks |
| PROC-042v2-B fora do top-5 (P4) | Com k=10, chunk de multiplicadores ficava nas posições 6–10 | k: `n*2` → `n*3` |
| PROC-042v2-B gap semântico residual (P4) | Texto "Norte \| 1.8" sozinho não conectava com "frete Manaus" | `enriquecer_tabelas` adiciona "Norte — Multiplicador: 1.8" (combinado com cidades do geo enrichment) |

---

## 6. Impacto esperado por pergunta

| Pergunta | Antes (v2) | Esperado (v3) |
|---|---|---|
| P1 — Prazo de devolução | POL-001-A ✅, POL-001-B ❌ | POL-001-A ✅, POL-001-B ✅ (seção 3.2 agora íntegra) |
| P2 — Carga perigosa devolução | POL-001-B fragmento ⚠️ | POL-001-B ✅ (chunk único com lista ANTT + ramal) |
| P3 — SLA Gold | SLA-2024-B ❌ | SLA-2024-B ✅ (enriquecimento textual da tabela) |
| P4 — Frete Manaus | PROC-042v2-A ✅, PROC-042v2-B ❌ | PROC-042v2-A ✅, PROC-042v2-B ✅ (k=15 + tabela narrativa + geo) |
| P5 — Perigosa + expresso | FAQ-32 ✅ | FAQ-32 ✅ (sem regressão esperada) |
| **Total obrigatórios** | **3/7 (43%)** | **7/7 (100%) esperado** |

---

## 7. Procedimento de reindexação

```bash
cd py-ia-first
python indexar_documentos.py
# Pasta dos .md  → caminho para arquivos-input
# Pasta ChromaDB → ./chroma_db (ou Enter)
# Forçar?        → s   ← obrigatório — todas as 4 alterações mudam o conteúdo dos chunks
```

Após reindexar, executar `pipe-rag.py` e comparar os novos prompts com o gabarito do Anexo B.
