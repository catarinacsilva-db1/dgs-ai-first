# Diagnóstico do Pipeline RAG — NovaTech

**Data:** 2026-06-19  
**Escopo:** Indexação (`indexar_documentos.py`) e Retriever (`retriever.py`)  
**Motivação:** Chunks retornados nas buscas estão incorretos ou ausentes em relação ao gabarito do Anexo B. Taxa de recuperação de chunks obrigatórios: 2/7 (29%).

---

## Resultado observado por pergunta

| Pergunta | Chunks obrigatórios (Anexo B) | Recuperados | Taxa |
|---|---|---|---|
| P1 — Prazo de devolução | POL-001-A, POL-001-B | POL-001-A ✅ | 1/2 (50%) |
| P2 — Carga perigosa devolução | POL-001-B | ❌ nenhum | 0/1 (0%) |
| P3 — SLA Gold | SLA-2024-B | ❌ nenhum | 0/1 (0%) |
| P4 — Frete Manaus 600kg | PROC-042v2-B, PROC-042v2-A | ❌ nenhum | 0/2 (0%) |
| P5 — Carga perigosa + expresso | FAQ-32 | FAQ-32 ✅ | 1/1 (100%) |

---

## 1. Diagnóstico da Indexação

### 1.1 `strip_headers=False` pode não estar disponível — Severidade: **Alta**

**Localização:** `indexar_documentos.py`, função `chunkar_por_headers`, linha 114.

```python
try:
    md_splitter = MarkdownHeaderTextSplitter(strip_headers=False)
except TypeError:
    md_splitter = MarkdownHeaderTextSplitter(...)  # sem strip_headers
```

**Como causa o problema:** Se o fallback for acionado, os cabeçalhos `##`/`###` são removidos do texto do chunk. O embedding perde o vocabulário da seção ("Prazo geral", "Multiplicadores regionais") — exatamente o que diferencia um chunk do outro semanticamente. Chunks sem o cabeçalho têm vetores mais genéricos e menos discriminativos.

**Como verificar:**
```bash
python -c "import langchain_text_splitters; print(langchain_text_splitters.__version__)"
# Versões < 0.2.x não têm strip_headers
```

**Correção:** Fixar versão mínima em `requirements.txt`:
```
langchain-text-splitters>=0.2.0
```

---

### 1.2 Bloco anterior ao primeiro `##` não é capturado — Severidade: **Média**

**Localização:** `indexar_documentos.py`, lista `headers_to_split_on`, linha 108.

```python
headers_to_split_on = [
    ("##",  "secao"),
    ("###", "subsecao"),
]
```

**Como causa o problema:** O `MarkdownHeaderTextSplitter` ignora o conteúdo antes do primeiro `##` — o título `#` e o bloco de metadados (Versão, Responsável, Data) não entram em nenhum chunk. Para documentos como SLA-2024, onde a seção 1 começa logo após o título, isso pode fazer o chunk de classificação de clientes ser descartado por tamanho < 30 chars se o bloco intro for mínimo.

**Como verificar:**
```python
chunks = chunkar_por_headers(content, doc_meta)
print(f"Total de chunks: {len(chunks)}")
for c in chunks:
    print(c.metadata.get('secao'), '|', c.page_content[:80])
```

**Correção:**
```python
headers_to_split_on = [
    ("#",   "titulo"),
    ("##",  "secao"),
    ("###", "subsecao"),
]
```

---

### 1.3 Enriquecimento geográfico pode não cobrir todos os chunks da PROC-042 — Severidade: **Média**

**Localização:** `indexar_documentos.py`, função `enriquecer_geograficamente`, linha 64.

```python
re.search(rf"\|\s*{regiao}\s*\|", texto)
```

**Como causa o problema:** O enriquecimento só ocorre em chunks que contêm a tabela regional completa no padrão `| Região |`. Se o fallback de 800 chars cortar a tabela no meio, a segunda metade dos dados regionais vai para um chunk sem o padrão detectável — e sem enriquecimento. A query "Frete para Manaus" pode não encontrar nenhum chunk com score ≥ 0.40.

**Como verificar:**
```python
proc_chunks = vectorstore.get(
    where={"source": "PROC-042-v2-frete-especial-revisado.md"}
)
for text in proc_chunks['documents']:
    enriquecido = "Manaus" in text
    print("ENRIQUECIDO:" if enriquecido else "NÃO ENRIQUECIDO:", text[:200])
```

**Correção:** Se a tabela for cortada, aumentar o `chunk_size` do fallback para 1200 ou aplicar o enriquecimento após o fallback também:
```python
for j, sub in enumerate(fallback_splitter.split_text(text)):
    sub = enriquecer_geograficamente(sub.strip())  # enriquecer cada sub-chunk
```

---

### 1.4 Reindexação incremental não detecta mudança de conteúdo — Severidade: **Média**

**Localização:** `indexar_documentos.py`, bloco de skip incremental, linha 245.

```python
existing = vectorstore.get(where={"source": doc["source"]})
if existing.get("ids"):
    skipped += 1
    continue
```

**Como causa o problema:** O skip usa apenas o nome do arquivo como critério. Se a estratégia de chunking mudou mas o arquivo tem o mesmo nome, o banco continua com os chunks antigos gerados pelo `RecursiveCharacterTextSplitter(size=500)`. Os prompts P3 e P4 retornando `[SEM CONTEXTO]` após as alterações sugerem que o banco não foi reindexado com `forcar_reindex=s`.

**Como verificar:**
```python
result = vectorstore.get(where={"source": "SLA-2024-tabela-sla.md"})
print(f"Chunks no banco: {len(result['ids'])}")
print(result['documents'][0][:300])  # verificar se é chunk estrutural ou por caractere
```

**Correção:** Sempre usar `forcar_reindex=s` após qualquer mudança de estratégia de chunking ou modelo de embedding.

---

### 1.5 IDs de chunk — Sem colisão confirmada

`doc_id` é derivado do nome completo do arquivo sem extensão (`PROC-042-v1-frete-especial` vs `PROC-042-v2-frete-especial-revisado`). Não há risco de colisão entre v1 e v2. ✅

---

## 2. Diagnóstico do Retriever

### 2.1 Modelo de embedding — Consistente entre indexação e retrieval ✅

Ambos `indexar_documentos.py` e `retriever.py` usam `all-MiniLM-L6-v2`. Não há inconsistência de espaço vetorial entre os embeddings dos documentos e das queries. ✅

---

### 2.2 Métrica de distância não configurada explicitamente — Severidade: **Média**

**Localização:** `indexar_documentos.py` e `retriever.py`, instanciação do `Chroma`.

```python
vectorstore = Chroma(collection_name="novatech_docs", ...)
```

**Como causa o problema:** ChromaDB usa cosine por padrão, mas `similarity_search_with_relevance_scores` do LangChain normaliza o score de formas diferentes dependendo da versão. Em algumas versões aplica `(1 - d) / 2`, em outras `1 - d`. Isso pode explicar scores uniformemente baixos (todos ~0.36) para P3 — a normalização pode estar comprimindo a escala.

**Como verificar — score bruto via ChromaDB direto:**
```python
results = vectorstore._collection.query(
    query_texts=["Qual o SLA do cliente Gold?"],
    n_results=10
)
print("Distâncias brutas:", results['distances'])
print("Documentos:", [d[:60] for d in results['documents'][0]])
```

**Correção:** Configurar explicitamente a métrica na criação da coleção:
```python
vectorstore = Chroma(
    collection_name="novatech_docs",
    embedding_function=embeddings,
    persist_directory=chroma_dir,
    collection_metadata={"hnsw:space": "cosine"}
)
```

---

### 2.3 `embed_query` chamado e descartado — Severidade: **Baixa**

**Localização:** `retriever.py`, linha 33.

```python
_ = embedding_model.embed_query(pergunta)  # resultado descartado
```

**Como causa o problema:** O LangChain re-embeda a query internamente em `similarity_search_with_relevance_scores`. Esta linha é um no-op — não causa falha mas adiciona latência desnecessária (uma chamada extra de embedding por query).

**Correção:** Remover a linha.

---

### 2.4 Threshold de 0.40 pode estar cortando chunks válidos do SLA-2024 — Severidade: **Alta**

**Localização:** `retriever.py`, parâmetro `score_minimo`, linha 11.

```python
score_minimo: float = 0.40
```

**Como causa o problema:** Com o modelo inglês `all-MiniLM-L6-v2`, queries em português geram scores uniformemente baixos. Os chunks do SLA-2024 podem estar chegando a scores de 0.35–0.39 — relevantes semanticamente, mas abaixo do threshold. O resultado é `[SEM CONTEXTO]` para P3 mesmo que os chunks existam no banco.

**Como verificar:**
```python
raw = vectorstore.similarity_search_with_relevance_scores(
    "Qual o SLA do cliente Gold?", k=20
)
for doc, score in raw:
    print(f"{score:.4f} | {doc.metadata.get('source')} | {doc.page_content[:80]}")
```

**Árvore de decisão:**

| Score dos chunks SLA-2024 | Diagnóstico | Ação |
|---|---|---|
| 0.40–1.00 | Threshold não é o problema | Investigar indexação |
| 0.30–0.39 | Threshold cortando válidos | Baixar para 0.35 ou trocar modelo |
| < 0.25 | Modelo inadequado para PT | Trocar modelo + reindexar |
| SLA-2024 não aparece nos top-20 | Chunk não foi indexado | Verificar indexação |

---

### 2.5 Modelo `all-MiniLM-L6-v2` é inglês — Causa estrutural principal — Severidade: **Alta**

**Localização:** `indexar_documentos.py` linha 226 e `pipe-rag.py` linha 19.

```python
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
```

**Como causa o problema:** Este modelo foi treinado predominantemente em inglês. Para documentos e queries em português, os vetores gerados têm baixa discriminação semântica — domínios diferentes (SLA, devolução, frete) ficam próximos no espaço vetorial, resultando em scores uniformes e baixos para todas as queries (observado: P3 todos os scores em ~0.36). 

Esta é a causa mais provável da falha total em P3 (SLA Gold) e contribuinte em P4 (Manaus).

**Correção definitiva:**
```python
# Substituir em indexar_documentos.py e pipe-rag.py:
model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# ou:
model_name = "sentence-transformers/distiluse-base-multilingual-cased-v2"
```

Requer reindexação completa com `forcar_reindex=s`.

---

## 3. Checklist de Validação

Execute os passos abaixo na ordem para isolar a causa antes de aplicar correções.

### Passo 1 — Confirmar que os chunks existem no banco

```python
for source in ["SLA-2024-tabela-sla.md",
               "PROC-042-v2-frete-especial-revisado.md",
               "POL-001-politica-devolucao.md",
               "FAQ-atendimento.md"]:
    result = vectorstore.get(where={"source": source})
    n = len(result['ids'])
    print(f"{source}: {n} chunks")
    if n > 0:
        print(f"  Exemplo: {result['documents'][0][:120]}\n")
```

**Esperado:** SLA-2024 com ≥ 5 chunks, PROC-042-v2 com ≥ 6 chunks.  
**Se 0 chunks:** arquivo não foi indexado — verificar path e rodar com `forcar_reindex=s`.

---

### Passo 2 — Testar scores brutos sem threshold

```python
queries = {
    "P1": "Qual o prazo de devolução?",
    "P2": "Posso devolver carga perigosa?",
    "P3": "Qual o SLA do cliente Gold?",
    "P4": "Frete para 600kg para Manaus?",
    "P5": "Carga perigosa com frete expresso?",
}

for label, query in queries.items():
    raw = vectorstore.similarity_search_with_relevance_scores(query, k=10)
    print(f"\n{label}: {query}")
    for doc, score in raw[:5]:
        src = doc.metadata.get('source', '')
        secao = doc.metadata.get('secao', '')
        print(f"  {score:.4f} | {src} | {secao} | {doc.page_content[:60]}")
```

---

### Passo 3 — Confirmar enriquecimento geográfico na PROC-042

```python
proc_chunks = vectorstore.get(
    where={"source": "PROC-042-v2-frete-especial-revisado.md"}
)
for i, text in enumerate(proc_chunks['documents']):
    enriquecido = "Manaus" in text
    secao = proc_chunks['metadatas'][i].get('secao', '')
    print(f"Chunk {i} | {secao} | Enriquecido: {enriquecido}")
```

**Esperado:** Pelo menos 1 chunk com `"Manaus"` presente (seção de multiplicadores regionais).

---

### Passo 4 — Confirmar metadados `is_latest` para PROC-042

```python
for source in ["PROC-042-v1-frete-especial.md",
               "PROC-042-v2-frete-especial-revisado.md"]:
    result = vectorstore.get(where={"source": source})
    for meta in result['metadatas'][:2]:
        print(f"{meta.get('source')} → is_latest: {meta.get('is_latest')}")
```

**Esperado:** v1 → `is_latest: false`, v2 → `is_latest: true`.

---

### Passo 5 — Confirmar versão do LangChain para `strip_headers`

```bash
python -c "
import langchain_text_splitters
print('langchain_text_splitters:', langchain_text_splitters.__version__)
from langchain_text_splitters import MarkdownHeaderTextSplitter
import inspect
sig = inspect.signature(MarkdownHeaderTextSplitter.__init__)
print('strip_headers disponível:', 'strip_headers' in sig.parameters)
"
```

---

### Interpretação dos resultados

| Resultado | Diagnóstico | Próxima ação |
|---|---|---|
| Passo 1: chunks ausentes | Arquivo não indexado ou path errado | Corrigir path + `forcar_reindex=s` |
| Passo 2: scores SLA < 0.30 | Modelo inglês inadequado | Trocar para multilíngue + reindexar |
| Passo 2: scores SLA 0.30–0.39 | Threshold cortando válidos | Baixar `score_minimo` para 0.35 temporariamente |
| Passo 2: scores SLA ≥ 0.40 mas não retornados | Bug no filtro do retriever | Revisar lógica de `valid_results` |
| Passo 3: nenhum chunk com "Manaus" | Enriquecimento não rodou | Confirmar reindexação forçada |
| Passo 4: `is_latest` ausente nos metadados | Banco com chunks antigos | Forçar reindexação completa |
| Passo 5: `strip_headers` indisponível | Cabeçalhos sendo removidos dos chunks | Atualizar `langchain-text-splitters` |

---

## Resumo de prioridades

| # | Falha | Severidade | Impacto direto |
|---|---|---|---|
| 1 | Modelo `all-MiniLM-L6-v2` inadequado para PT | Alta | P3, P4 com falha total |
| 2 | `strip_headers` indisponível na versão instalada | Alta | Embeddings degradados em todos os chunks |
| 3 | Banco não reindexado com nova estratégia | Alta | Chunks antigos ainda em uso |
| 4 | Threshold 0.40 cortando chunks válidos | Alta | P3 sem contexto mesmo com chunks no banco |
| 5 | Métrica de distância não configurada explicitamente | Média | Normalização de scores inconsistente |
| 6 | Enriquecimento não aplicado após fallback splitter | Média | P4 sem enriquecimento em tabelas longas |
| 7 | Bloco pré-`##` descartado | Média | Perda de contexto introdutório |
| 8 | `embed_query` chamado e descartado | Baixa | Latência extra por query |
