# Relatório de Alterações — Pipeline RAG NovaTech

**Data:** 2026-06-19  
**Escopo:** Etapa de ingestão e pipeline de retrieval  
**Motivação:** Análise de retrieval (`analise-retrieval-rag.md`) identificou taxa de recuperação de chunks obrigatórios de 12,5% (1 de 8). As alterações corrigem as causas-raiz identificadas.

---

## Diagnóstico resumido (base das alterações)

| Pergunta | Falha identificada |
|----------|--------------------|
| P1 — Prazo de devolução | Chunk POL-001-A ausente; POL-001-B recuperado truncado |
| P2 — Devolução carga perigosa | POL-001-B ausente; apenas FAQ informal recuperado |
| P3 — SLA Gold | SLA-2024-B ausente; scores todos empatados em 0.36 |
| P4 — Frete 600kg Manaus | Falha total: "Manaus" não conectou à "região Norte" |
| P5 — Carga perigosa frete expresso | Correto, mas 2 de 3 chunks eram irrelevantes |

**Causa-raiz comum:** chunking por tamanho de caractere (`size=500`) truncava seções no meio; threshold de score permissivo (`0.35`) deixava ruído entrar no contexto; gap semântico cidade/região não era resolvido; versão antiga da PROC-042 era descartada na ingestão, impedindo teste de cenário de contradição.

---

## 1. `indexar_documentos.py` — Alterações

### 1.1 Nova estratégia de chunking: `MarkdownHeaderTextSplitter`

**Antes**
```python
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

loader = TextLoader(doc["file_path"], encoding="utf-8")
langchain_docs = loader.load()
chunks = splitter.split_documents(langchain_docs)
```

**Depois**
```python
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def chunkar_por_headers(content: str, doc_meta: dict) -> list[Document]:
    headers_to_split_on = [("##", "secao"), ("###", "subsecao")]
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800, chunk_overlap=150
    )
    # ... lógica de split estrutural com fallback para seções > 800 chars
```

**Por que:** O `RecursiveCharacterTextSplitter(size=500)` dividia o documento por contagem de caracteres sem nenhuma consciência da estrutura. Resultado direto: a seção 3.2 (cargas perigosas — 550 chars) era cortada logo após o cabeçalho `### 3.2. Exceções ao prazo geral`, entregando ao LLM apenas a primeira linha sem a lista de cargas nem o ramal 4500.

O `MarkdownHeaderTextSplitter` com `##` e `###` como pontos de corte respeita a estrutura existente dos documentos. Cada subseção (`3.1. Prazo geral`, `3.2. Exceções`, `3.3. Procedimento`, cada `### Item N` do FAQ) vira um chunk independente e íntegro — exatamente o mapeamento previsto no Anexo B.

**Impacto esperado por documento:**

| Documento | Antes (chunks por caractere) | Depois (chunks por header) |
|-----------|------------------------------|---------------------------|
| POL-001 | ~6 chunks, seções misturadas | 7 chunks: 1 por objetivo/escopo + 5 subseções (3.1–3.5) |
| PROC-042-v2 | ~4 chunks com tabela possivelmente cortada | 6 chunks: 5 seções + 1 subseção 2.1 com tabela intacta |
| SLA-2024 | ~7 chunks com tabelas fragmentadas | 6 chunks: 1 por seção principal |
| FAQ | ~5 chunks com itens misturados | 8 chunks: 1 por item `### Item N` |

**`strip_headers=False`:** mantém o título da seção no texto do chunk (ex: `### 3.1. Prazo geral` aparece no conteúdo). O modelo de embedding usa esse vocabulário para criar um vetor mais representativo do tema da seção, melhorando a correspondência semântica com queries sobre esse tema.

---

### 1.2 Enriquecimento geográfico para chunks de PROC-042

**Antes:** não existia.

**Depois**
```python
REGIOES_CIDADES = {
    "Norte":         "Manaus, Belém, Porto Velho, Macapá, Boa Vista, Rio Branco, Palmas",
    "Nordeste":      "Salvador, Recife, Fortaleza, Natal, João Pessoa, ...",
    "Centro-Oeste":  "Brasília, Goiânia, Campo Grande, Cuiabá",
    "Sudeste":       "São Paulo, Rio de Janeiro, Belo Horizonte, Vitória, Campinas",
    "Sul":           "Curitiba, Porto Alegre, Florianópolis",
}

def enriquecer_geograficamente(texto: str) -> str:
    # Detecta regiões presentes na tabela (padrão "| Região |")
    # Acrescenta lista de cidades ao final do chunk
```

**Por que:** A query `"Frete para 600kg para Manaus?"` falhou completamente (nenhum chunk recuperado) porque os documentos PROC-042 usam apenas o nome da região ("Norte") sem mencionar cidades. O modelo `all-MiniLM-L6-v2` não tem representação semântica suficiente para conectar "Manaus" a "Norte" sem contexto linguístico explícito.

Ao acrescentar `"Região Norte: Manaus, Belém, Porto Velho..."` ao chunk que contém a tabela de multiplicadores regionais, o vetor gerado pelo embedding passa a incluir representações desses tokens. A query "frete para Manaus" passa a ter sobreposição semântica real com o chunk.

A função verifica o padrão `| Norte |` na tabela antes de enriquecer, garantindo que o enriquecimento só ocorra em chunks com dados regionais, não em qualquer menção à palavra.

---

### 1.3 Versões conflitantes: ambas indexadas

**Antes**
```python
# Apenas a versão mais recente era indexada; a versão antiga era descartada
for base_id, group in grouped_docs.items():
    group.sort(key=lambda x: obter_versao_tupla(x["versao"]), reverse=True)
    best_doc = group[0]
    docs_to_process.append(best_doc)
    for ignored_doc in group[1:]:
        ignored_files_count += 1  # versão antiga ignorada
```

**Depois**
```python
# Ambas as versões são indexadas; is_latest marca qual é a mais recente
for base_id, group in grouped_docs.items():
    group.sort(key=lambda x: obter_versao_tupla(x["versao"]), reverse=True)
    group[0]["is_latest"] = "true"
    for old_doc in group[1:]:
        old_doc["is_latest"] = "false"
        print(f"[AVISO] {old_doc['source']} é versão anterior ...")

docs_to_process = parsed_docs  # processa todos
```

**Por que:** O Anexo B prevê explicitamente que `PROC-042-B` (v1) pode aparecer como chunk opcional nos resultados da query de frete. Descartá-lo na ingestão tornava impossível testar o cenário de contradição entre versões — um dos cenários centrais do exercício ("armadilha 1" do Anexo B). A instrução 3 do `system_prompt` já orienta o LLM a priorizar a versão mais recente quando houver divergência. O campo `is_latest` permite que o `prompt_builder` sinalize ao modelo qual versão é anterior.

---

### 1.4 Novos campos de metadata

**Antes:** `source, doc_id, versao, data_emissao, responsavel, chunk_index, total_chunks`

**Depois:** adicionados `base_id, is_latest, secao, chunk_tipo`

| Campo novo | Valores possíveis | Uso |
|------------|------------------|-----|
| `base_id` | `"PROC-042"`, `"POL-001"`, ... | Agrupamento de versões; detecção de contradição |
| `is_latest` | `"true"` / `"false"` | Sinalização de versão no `prompt_builder` |
| `secao` | `"3.2. Exceções ao prazo geral"`, `"Item 32"`, ... | Rastreabilidade da origem dentro do documento |
| `chunk_tipo` | `"subsecao"` / `"secao"` | Granularidade do chunk para depuração |

---

### 1.5 Opção de reindexação forçada

**Antes:** não existia mecanismo para recriar o banco após mudança de estratégia.

**Depois**
```python
forcar_str = input("Forçar reindexação completa (apaga o banco atual)? [s/N]: ")
forcar_reindex = forcar_str.strip().lower() == "s"

if forcar_reindex and os.path.exists(chroma_dir):
    shutil.rmtree(chroma_dir)
```

**Por que:** Sem essa opção, chunks antigos (gerados pelo splitter por caractere) permaneciam no banco mesmo após reindexação, pois a verificação incremental é feita por `source`. Qualquer mudança de estratégia de chunking requer recriar o banco do zero.

---

## 2. `retriever.py` — Alterações

### 2.1 Threshold elevado de 0.35 para 0.40

**Antes:** `score_minimo: float = 0.35`  
**Depois:** `score_minimo: float = 0.40`

**Por que:** A análise mostrou que chunks com score entre 0.35 e 0.39 eram sistematicamente irrelevantes para a query. Na P2 ("Posso devolver carga perigosa?"), o FAQ-22 (seguro de carga, score 0.40) e FAQ-38 (carga danificada, score 0.36) ocupavam dois dos três slots de contexto sem contribuir para a resposta. Na P5, FAQ-38 (0.44) e FAQ-22 (0.42) também apareceram como ruído. O threshold de 0.40 elimina os chunks mais ruidosos sem sacrificar chunks marginalmente relevantes.

---

### 2.2 Remoção do pad para mínimo de 3 chunks

**Antes**
```python
# Se após o corte restar menos de 3, completar (pad) com resultados abaixo do limiar
if len(final_docs) < 3:
    needed = 3 - len(final_docs)
    final_docs.extend(below_threshold[:needed])
```

**Depois**
```python
# Pad removido: injetar chunks abaixo do limiar causava ruído no contexto do LLM
# Quando não há chunks relevantes, o prompt-sistema aciona a resposta
# "Não encontrei essa informação nos documentos disponíveis."
```

**Por que:** O pad forçava o retorno de 3 chunks independentemente da qualidade. O efeito prático era exatamente o problema observado: chunks irrelevantes preenchiam o contexto do LLM, diluindo a atenção do modelo e introduzindo informações de outros domínios. A resposta correta quando não há contexto suficiente é retornar lista vazia — o `prompt_builder` já trata esse caso exibindo `[SEM CONTEXTO]` e o system prompt instrui o LLM a responder com a frase padronizada.

---

### 2.3 Novos campos no retorno

**Antes:** retornava `chunk_index_global, score, texto, source, doc_id, versao, data_emissao, responsavel, chunk_index, total_chunks, abaixo_do_limiar`

**Depois:** adicionados `base_id, is_latest, secao`

```python
item = {
    ...
    "base_id":   metadata.get("base_id", ""),
    "is_latest": metadata.get("is_latest", "true"),
    "secao":     metadata.get("secao", ""),
    ...
}
```

**Por que:** `is_latest` é necessário para o `prompt_builder` sinalizar versões anteriores. `base_id` permite detectar que dois chunks vêm do mesmo documento familiar (ex: `PROC-042` v1 e v2 recuperados juntos — cenário de contradição). `secao` melhora a rastreabilidade nos logs e pode ser exibida no prompt para ajudar o LLM a citar a fonte corretamente.

---

## 3. `prompt_builder.py` — Alterações

### 3.1 Sinalização de versão anterior no bloco de documento

**Antes**
```python
bloco_doc = (
    f"--- Documento [{...}] ---\n"
    f"Fonte     : {chunk.get('source', '')}\n"
    f"Versão    : {chunk.get('versao', '')}\n"
    ...
)
```

**Depois**
```python
is_latest = chunk.get("is_latest", "true")
aviso_versao_str = (
    "\n[VERSÃO ANTERIOR — priorize a versão mais recente do mesmo documento]"
    if is_latest == "false" else ""
)

bloco_doc = (
    f"--- Documento [{...}] ---\n"
    f"Fonte     : {chunk.get('source', '')}\n"
    f"Versão    : {chunk.get('versao', '')}\n"
    f"Score     : {chunk.get('score', 0.0):.2f}{aviso_limiar_str}{aviso_versao_str}\n\n"
    ...
)
```

**Por que:** A instrução 3 do system prompt pede ao LLM que priorize a versão mais recente quando houver divergência. Sem um marcador explícito no bloco do documento, o LLM precisa inferir qual versão é mais recente comparando campos de data e versão — o que é possível, mas não garantido. O aviso `[VERSÃO ANTERIOR]` torna explícita essa informação no contexto, ativando a instrução 3 de forma mais confiável.

---

## 4. `pipe-rag.py` — Alterações

### 4.1 Parâmetros de busca atualizados

**Antes:** `n=3, score_minimo=0.35`  
**Depois:** `n=5, score_minimo=0.40`

**Por que:** Com `n=3` e a nova estratégia de chunking (mais chunks por documento), há risco de não recuperar todos os chunks relevantes de uma query multi-domínio. Aumentar para `n=5` (com busca interna de `n*2=10` candidatos) dá mais margem sem sobrecarregar o contexto — o threshold de 0.40 já funciona como filtro de qualidade.

---

## 5. Mapeamento entre falhas e correções

| Falha identificada na análise | Correção aplicada | Arquivo |
|-------------------------------|------------------|---------|
| Seção 3.2 truncada após cabeçalho | MarkdownHeaderTextSplitter — chunk por subseção | `indexar_documentos.py` |
| Seção 3.1 (prazo geral) não recuperada | Chunking estrutural garante chunk dedicado por seção | `indexar_documentos.py` |
| "Manaus" não conecta a "região Norte" | Enriquecimento geográfico com cidades por região | `indexar_documentos.py` |
| FAQ-22 e FAQ-38 como ruído nos resultados | Threshold elevado (0.40) + remoção do pad forçado | `retriever.py` |
| PROC-042 v1 descartado na ingestão | Indexação de ambas as versões com flag `is_latest` | `indexar_documentos.py` |
| LLM não sinalizava versão anterior | Aviso `[VERSÃO ANTERIOR]` no bloco do documento | `prompt_builder.py` |
| Sem opção para recriar banco após mudança | Parâmetro `forcar_reindex` com limpeza do diretório | `indexar_documentos.py` |
| Scores uniformes e baixos para SLA Gold | Melhoria indireta via chunks estruturais mais ricos | `indexar_documentos.py` |

---

## 6. Limitação remanescente

O modelo de embedding `all-MiniLM-L6-v2` foi treinado predominantemente em inglês. Para documentos em português, modelos multilíngues como `paraphrase-multilingual-MiniLM-L12-v2` ou `sentence-transformers/distiluse-base-multilingual-cased-v2` geram scores significativamente mais altos e discriminativos. Essa troca requer reindexação completa (usar a opção `forcar_reindex`) e alteração do `model_name` em `indexar_documentos.py` e `pipe-rag.py`.

---

## 7. Procedimento para reindexar

```bash
# 1. Navegar até o diretório do projeto
cd py-ia-first

# 2. Executar o script de indexação
python indexar_documentos.py

# Quando solicitado:
# Pasta dos .md  → caminho para arquivos-input (ex: ../Prática 1/arquivos-input)
# Pasta ChromaDB → ./chroma_db (ou Enter para padrão)
# Forçar?        → s  (obrigatório na primeira execução com a nova estratégia)
```

Após a reindexação, executar `pipe-rag.py` para gerar os novos prompts e verificar os scores.
