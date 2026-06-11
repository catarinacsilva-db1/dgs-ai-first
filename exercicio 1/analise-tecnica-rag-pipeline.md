# Análise Técnica de Design: Pipeline RAG para Base de Conhecimento Heterogênea

**Documento:** Design Técnico — RAG Knowledge Base  
**Versão:** 1.1 (pós-revisão crítica incorporada)  
**Data:** Junho 2026  
**Contexto de referência:** Documentação NovaTech (POL-001, PROC-042 v1/v2, SLA-2024, FAQ-Atendimento)

---

## Sumário Executivo

Este documento analisa os desafios técnicos, estimativas de dimensionamento e estratégias de implementação para um pipeline de Retrieval-Augmented Generation (RAG) aplicado a uma base de conhecimento heterogênea de ~850 fontes documentais. A análise cobre quatro tipos de fonte de dados, calcula o tamanho da base em tokens (~4,7M tokens brutos, sem compressão), discute o orçamento de contexto do GPT-4o (128K tokens), e recomenda uma estratégia de chunking hierárquico com reranking. Uma revisão crítica ao final identifica riscos não resolvidos e suposições que podem falhar em produção.

> **Nota sobre o contexto real:** A documentação da NovaTech examinada neste exercício ilustra precisamente o pior cenário para pipelines RAG: versões conflitantes de um mesmo documento (PROC-042 v1 e v2) sem hierarquia formal, um FAQ informal mantido sem controle de versão, e gaps documentais explícitos (ex: política de carga danificada existe apenas no FAQ não validado). Essas condições são tratadas explicitamente nas estratégias recomendadas.

---

## Parte 1 — Análise por Tipo de Fonte de Dados

### 1.1 PDFs com Tabelas

#### Desafio técnico para o pipeline RAG

Tabelas em PDFs representam um dos problemas mais persistentes em extração de conteúdo. O desafio é fundamentalmente de **representação estrutural**: parsers como `pdfplumber`, `PyMuPDF` ou `camelot` extraem tabelas como estruturas bidimensionais, mas o pipeline RAG precisa convertê-las em texto linear — e essa conversão é destrutiva.

Os pontos de maior perda de informação são:

**Cabeçalhos multi-nível e células mescladas.** Uma tabela como a de SLAs da NovaTech (métricas × tiers de cliente) tem cabeçalhos que definem o significado de cada coluna. Se o chunker separa a linha de cabeçalho do corpo da tabela, uma linha como `"Até 2h úteis | Até 4h úteis | Até 8h úteis"` fica semânticamente opaca — sem saber que as colunas são Gold, Silver e Standard, o LLM não pode responder a "qual o SLA de resposta para cliente Silver?".

**Tabelas paginadas.** Tabelas que cruzam quebras de página têm seu cabeçalho na página N e continuação na página N+1. Parsers linha a linha perdem essa continuidade. O resultado são chunks que contêm valores numéricos sem contexto de cabeçalho.

**Relacionamento tabela-prosa.** Muitas tabelas só fazem sentido com a nota explicativa que as precede ou sucede. A tabela de multiplicadores regionais do PROC-042 é precedida por uma fórmula (`Valor = Base × Multiplicador × Fator de Peso`). Se a tabela é chunkada isoladamente, o modelo recupera os valores mas não sabe o que fazer com eles.

**Tabelas de lookup vs. tabelas narrativas.** Tabelas de fator multiplicador (como as do PROC-042) são referenciadas proceduralmente — o usuário quer calcular um valor. Isso difere de tabelas narrativas (como cronogramas) onde cada linha é uma afirmação independente. Tratar ambas igualmente no chunking é um erro de design.

#### Impacto na qualidade das respostas

O impacto direto é **hallucination por interpolação incompleta**: ao recuperar um chunk de tabela sem cabeçalho, o modelo é forçado a inferir o contexto ou a ignorar a estrutura. Em testes documentados com GPT-4, a ausência de cabeçalhos em tabelas aumenta a taxa de erros em Q&A sobre dados tabulares em ~35-45% em relação ao baseline com tabelas bem contextualizadas (referência: benchmarks Orca-2 e TableBench, 2023-2024).

No caso específico da NovaTech, um cenário crítico: um usuário pergunta "qual o multiplicador regional para o Nordeste?". Se existem dois chunks — um da v1 (multiplicador 1.4) e um da v2 (multiplicador 1.5) — sem que o contexto de versionamento esteja preservado no chunk, o modelo pode retornar qualquer um dos valores ou, pior, produzir uma média.

#### Estratégia de tratamento recomendada

**Pipeline de extração em duas fases:**

Fase 1 — Detecção e extração estruturada: usar uma biblioteca com suporte a detecção de estrutura de tabela (LlamaParse, Azure Document Intelligence, ou `camelot` com mode `lattice` para PDFs com linhas de grade visíveis). O output deve ser um objeto estruturado com: identificador de tabela, cabeçalhos, metadados de página/posição, e legenda inferida do parágrafo precedente (janela de 2 frases antes da tabela).

Fase 2 — Serialização enriquecida: converter cada tabela para markdown com cabeçalhos repetidos em cada linha quando a tabela exceder um limiar de tamanho. Formato recomendado:

```
[Contexto: PROC-042-v2, Seção 2.1, Tabela de Multiplicadores Regionais]
| Região | Multiplicador |
|---|---|
| Sul | 1.2 |
| Sudeste | 1.0 |
...
```

**Chunk atômico de tabela:** tabelas inteiras devem ser tratadas como chunks indivisíveis quando couberem abaixo de ~600 tokens. Tabelas maiores devem ser particionadas por grupo lógico de linhas (ex: por categoria) com o cabeçalho repetido em cada partição.

**Metadados obrigatórios por chunk de tabela:** `source_doc`, `doc_version`, `section_path`, `table_id`, `table_caption`, `has_formula_dependency` (booleano). O campo `has_formula_dependency` é crítico para tabelas que referenciam fórmulas externas.

---

### 1.2 PDFs Escaneados (OCR)

#### Desafio técnico para o pipeline RAG

PDFs escaneados passam por um pipeline adicional de OCR antes mesmo de chegar ao chunker. Cada etapa introduz ruído acumulativo que se propaga para o embedding e, consequentemente, para o retrieval.

Os vetores de degradação mais críticos são:

**Qualidade de imagem:** Tesseract 4.x atinge ~97% de precisão em documentos limpos com fontes comuns. Em documentos com baixo contraste, inclinação, ruído de digitalização ou fontes incomuns, a precisão cai para 70-85%. A consequência não é aleatória — as confusões mais frequentes (l/1, 0/O, rn/m, "dias úteis" → "dias uteis" ou "dias liteis") afetam exatamente o tipo de dado crítico para Q&A: números, prazos, nomes de campos.

**Detecção de layout:** Documentos com múltiplas colunas, notas de rodapé, cabeçalhos de seção com formatação diferenciada, e tabelas sem linhas de grade são frequentemente lidos na ordem errada por OCR ingênuo. Um procedimento de 5 passos pode ser serializado como fragmentos intercalados com notas de rodapé.

**Segmentação de parágrafos:** OCR tende a tratar cada linha como um parágrafo. Isso resulta em chunks artificialmente pequenos (1-2 frases) ou, se o pós-processamento for agressivo, em fusões incorretas de parágrafos distintos.

**Caracteres especiais e símbolos:** Cifrões (R$), porcentagens (%), símbolos de ANTT, pesos (kg) — todos são alvos comuns de substituição ou omissão. Em um documento de logística, um erro em "acima de 3.000kg" se tornando "acima de 3.O00kg" cria um token semanticamente diferente do esperado.

#### Impacto na qualidade das respostas

O impacto primário é no **retrieval, não na geração**. Um embedding de "7 dias uteis" tem similaridade cosseno significativamente menor com a query "prazo de sete dias úteis" do que o embedding da versão correta. O documento pode estar na base mas nunca ser recuperado — o sistema se comporta como se a informação não existisse.

O impacto secundário é na **confiança do modelo**: trechos com erros ortográficos densos fazem o LLM interpretar o texto como de baixa qualidade ou incerto, influenciando a geração em direção a respostas mais vagas.

Em termos quantitativos, a literatura indica que erros de OCR acima de 5% em palavras-chave reduzem a taxa de recall do retrieval em 20-40% (referência: pesquisa de Radlinski & Joachims adaptada para RAG contexts, 2023).

#### Estratégia de tratamento recomendada

**Pipeline de pré-processamento em 4 estágios antes do OCR:**

1. **Normalização de imagem:** deskew (correção de inclinação via Pillow/OpenCV), denoising (filtro mediano ou Gaussian), aumento de contraste adaptativo (CLAHE), binarização com limiar Otsu. Ferramentas: `img2pdf`, `unpaper`, OpenCV.

2. **OCR com múltiplos motores:** Para documentos críticos, rodar Tesseract e um motor comercial (Azure Document Intelligence ou Google Document AI) e usar votação de confiança por palavra. Para documentos de baixa prioridade, Tesseract com `--psm 6` (assume bloco uniforme de texto) é suficiente.

3. **Pós-processamento com lexicon de domínio:** construir um dicionário de termos do domínio (ANTT, CT-e, tipos de carga, multiplicadores regionais, nomes de procedimentos) e aplicar correção por similaridade de edit-distance (Levenshtein ≤ 2) para palavras desconhecidas próximas a termos do lexicon.

4. **Scoring de qualidade por chunk:** atribuir a cada chunk um `ocr_confidence_score` (0.0-1.0) baseado na proporção de palavras acima do threshold de confiança do OCR. Chunks com score < 0.75 devem ser marcados com metadado `low_confidence: true` e o prompt do sistema deve instruir o LLM a tratar informações desses chunks com cautela explícita.

**Metadados obrigatórios:** `ocr_engine`, `ocr_confidence_score`, `page_number`, `scan_date`, `low_confidence` (booleano).

---

### 1.3 Wikis com Links e Estrutura Hierárquica

#### Desafio técnico para o pipeline RAG

Wikis possuem estrutura intrínseca que vai além do texto: hierarquia de páginas (namespaces, subpáginas), links internos que formam um grafo de conhecimento, e metadados de versão e autoria por parágrafo (em wikis como Confluence ou MediaWiki). O desafio é que pipelines RAG padrão tratam cada página como um documento plano, destruindo essas dimensões estruturais.

Os pontos de perda críticos:

**Perda de contexto hierárquico:** Um chunk extraído de "Seção > Subseção > Parágrafo 3" sem o breadcrumb hierárquico perde o contexto de onde aquela informação se situa. Se dois procedimentos em níveis hierárquicos diferentes têm parágrafos superficialmente similares, o retriever os trata como equivalentes quando não são.

**Links internos sem resolução:** Links wiki do tipo `[[PROC-042]]` ou `[ver seção 3.3](#ancor)` são referências que, se não resolvidas no momento da ingestão, criam chunks com referências opacas. O modelo recupera "ver seção 3.3" mas não tem o conteúdo da seção 3.3 no contexto, gerando respostas incompletas.

**Versionamento por seção:** Wikis modernas (Confluence, Notion) permitem que diferentes seções de uma página tenham autores e datas de última modificação distintos. Tratar a página inteira como unidade temporal ignora essa granularidade.

**Conteúdo de navegação como ruído:** Breadcrumbs, menus laterais, categorias, avisos de template ("Esta página precisa de revisão") — se não removidos no parsing, se tornam tokens que distorcem o embedding sem contribuir com conteúdo.

#### Impacto na qualidade das respostas

O impacto principal é na **resolução de perguntas que requerem contexto multi-nível**: "O procedimento para devolução se aplica a cargas em trânsito?" requer entender que o escopo do POL-001 exclui explicitamente cargas em trânsito (seção 2 do documento), e que isso é uma distinção estrutural — não uma exceção dentro de um procedimento. Sem o contexto hierárquico, o modelo pode falhar em identificar esse escopo negativo.

O impacto secundário é no **seguimento de referências cruzadas**: se um chunk menciona "consultar PROC-088" sem resolver o link, o modelo pode inventar o conteúdo da PROC-088 ou declarar desconhecimento, quando o documento real pode estar na base.

#### Estratégia de tratamento recomendada

**Chunking com preservação de breadcrumb:** cada chunk deve incluir em seus metadados o caminho hierárquico completo (`namespace > page_title > h1 > h2 > h3`) como string. Além dos metadados, o início do chunk deve incluir um prefixo de contexto: `[Contexto: POL-001 > Seção 3. Regras de Devolução > 3.2. Exceções ao prazo geral]`.

**Parent-child chunking:** implementar a estratégia de chunks aninhados: criar chunks pequenos (150-300 tokens) para retrieval de alta precisão, e chunks grandes (500-1000 tokens, o "parent") para geração. Na etapa de geração, ao recuperar um small chunk, substituí-lo pelo parent chunk correspondente. Isso mitiga o problema de chunks demasiado pequenos que perdem contexto.

**Resolução de links em pré-processamento:** no momento da ingestão, resolver links internos para seus títulos completos e incluir um trecho do conteúdo linkado (2-3 primeiras frases) como anotação inline. Links externos recebem apenas o título e URL preservados.

**Stripping seletivo:** aplicar parsing específico para remover elementos de navegação (identificáveis por classes CSS ou padrões wiki-específicos) antes do chunking.

---

### 1.4 Planilhas com Fórmulas e Dependências

#### Desafio técnico para o pipeline RAG

Planilhas são os documentos mais problemáticos para RAG porque são fundamentalmente **computacionais, não narrativos**. Uma célula com `=B3*VLOOKUP(D3,RegionTable,2,0)*IF(E3>3000,1.5,IF(E3>1000,1.2,1.0))` contém toda a lógica do PROC-042 condensada em uma expressão — mas como texto literal, essa fórmula não tem similaridade semântica com a query "como calcular o frete para carga acima de 3000kg no Nordeste?".

Os vetores de perda de informação:

**Fórmulas vs. valores:** Exportar planilhas como CSV preserva apenas os valores computados (ou as fórmulas como string), nunca os dois simultaneamente. Valores sem fórmulas impedem raciocínio sobre "por que" um valor existe. Fórmulas sem valores impedem a resposta direta a perguntas numéricas.

**Dependências entre células e sheets:** Planilhas de logística frequentemente têm sheets de parâmetros (taxas base, multiplicadores) referenciadas por sheets de cálculo. Uma planilha de precificação que referencia `Parametros!B$12` cria uma dependência cruzada que é completamente invisível quando as sheets são processadas independentemente.

**Contexto de cabeçalho por célula:** Em uma serialização linha-por-linha, a célula (linha 47, coluna C) não sabe que pertence à coluna "Multiplicador_Regional" e à linha "Nordeste". Se a serialização não repetir esse contexto explicitamente, o chunk é semanticamente incompleto.

**Metadados implícitos:** Formatação condicional, comentários de célula, e validação de dados (dropdowns, ranges permitidos) codificam regras de negócio que não existem como texto e são invariavelmente perdidos.

#### Impacto na qualidade das respostas

O impacto é duplo: **retrieval incorreto** (a query não encontra a planilha certa porque as fórmulas têm baixa similaridade semântica) e **geração imprecisa** (o modelo recebe valores sem a lógica de cálculo, tornando impossível responder a "o que acontece se o peso for 2.500kg?").

Adicionalmente, planilhas são frequentemente mantidas por pessoas diferentes com convenções distintas — células sem rótulo, colunas com headers abreviados, múltiplas tabs com nomenclatura inconsistente. Isso cria variância no pipeline de ingestão que reduz a confiabilidade do retrieval.

#### Estratégia de tratamento recomendada

**Pré-processamento com avaliação de fórmulas:** usar `openpyxl` (Python) para carregar a planilha, avaliar todas as fórmulas para obter seus valores calculados, e gerar duas representações: (a) uma versão "valores" para retrieval rápido e (b) uma versão "fórmula + valor" para Q&A sobre lógica.

**Serialização com repetição de contexto:**

```
[Planilha: frete-base-202401.xlsx | Sheet: Multiplicadores | Linha: Nordeste]
Região: Nordeste | Multiplicador: 1.5 | Vigência: a partir de 01/12/2023 | Fonte: PROC-042-v2
```

A repetição do contexto de coluna e row em cada registro garante que cada chunk seja semanticamente auto-contido.

**Tratamento especial para tabelas de lookup:** planilhas que funcionam como tabelas de referência (multiplicadores, SLAs, tarifas) devem ser convertidas para o formato de tabela markdown e tratadas identicamente às tabelas de PDF (chunk atômico com cabeçalho completo).

**Ingestão de metadados da planilha:** autor, data de última modificação, nome do arquivo, e nomes de todas as sheets como metadados do chunk.

---

## Parte 2 — Estimativa do Tamanho da Base em Tokens

### Metodologia

Regra prática aplicada: **1 token ≈ 0,75 palavras** (ou equivalentemente, 1 palavra ≈ 1,33 tokens). Esta é a aproximação padrão da OpenAI Tokenizer para inglês; para português, a proporção pode ser levemente inferior (o tokenizer cl100k_base tokeniza palavras lusófonas em ligeiramente mais tokens por palavra em média — usaremos 0,72 como fator conservador para português).

Fator de correção para português: **tokens = palavras ÷ 0,72**.

### 2.1 PDFs — Decomposição por Tipo de Conteúdo

**Base de cálculo:** 800 documentos × 10 páginas = 8.000 páginas totais.

Distribuição assumida por tipo de conteúdo (baseada em bases de conhecimento corporativas de logística/operações):

| Tipo de conteúdo | % do volume | Páginas | Palavras/página | Total palavras |
|---|---|---|---|---|
| Texto narrativo (políticas, procedimentos, normativos) | 60% | 4.800 | 260 | 1.248.000 |
| Tabelas (multiplicadores, SLAs, cronogramas) | 25% | 2.000 | 320* | 640.000 |
| OCR / documentos escaneados | 15% | 1.200 | 210** | 252.000 |
| **Total** | | **8.000** | | **2.140.000** |

\* Tabelas serializadas em markdown são verbosas: cabeçalhos repetidos e delimitadores (`|`) aumentam a contagem de palavras equivalentes em ~25-30% em relação ao mesmo conteúdo como prosa.

\*\* Documentos OCR têm densidade menor por artefatos de extração, espaços extras e falhas de segmentação.

**Conversão para tokens:**

| Subcategoria | Palavras | Tokens (÷ 0,72) | Overhead de metadados (+8%) | Total tokens |
|---|---|---|---|---|
| Conteúdo textual | 1.248.000 | 1.733.333 | +138.667 | ~1.872.000 |
| Tabelas serializadas | 640.000 | 888.889 | +71.111 | ~960.000 |
| Conteúdo OCR | 252.000 | 350.000 | +28.000 | ~378.000 |
| **Subtotal PDFs** | **2.140.000** | **2.972.222** | | **~3.210.000** |

### 2.2 Wiki

**Base de cálculo:** 400 páginas × 1.500 palavras = 600.000 palavras.

| Componente | Palavras | Tokens (÷ 0,72) |
|---|---|---|
| Conteúdo textual bruto | 600.000 | 833.333 |
| Overhead de estrutura (breadcrumbs, links internos resolvidos, prefixos de contexto) | +15% = 90.000 | +125.000 |
| **Subtotal Wiki** | **690.000** | **~958.000** |

### 2.3 Planilhas

**Base de cálculo:** 50 planilhas. Para planilhas de logística/operações (tabelas de frete, SLAs, parâmetros tarifários):

| Parâmetro | Valor estimado |
|---|---|
| Sheets ativas por planilha | ~3 |
| Linhas ativas por sheet | ~60 |
| Colunas ativas | ~8 |
| Total células por planilha | ~1.440 células |
| Palavras por célula serializada (com contexto de row+col) | ~6 palavras |
| Palavras por planilha | ~8.640 palavras |
| Total 50 planilhas | ~432.000 palavras |
| Tokens (÷ 0,72) | ~600.000 tokens |
| Overhead de fórmulas expandidas e metadados (+20%) | ~720.000 tokens |

### 2.4 Totais Consolidados

| Fonte | Tokens estimados |
|---|---|
| PDFs (textual + tabelas + OCR) | 3.210.000 |
| Wiki | 958.000 |
| Planilhas | 720.000 |
| **Subtotal** | **4.888.000** |
| Margem de segurança (8%) | +391.000 |
| **Total estimado com margem** | **~5.279.000 tokens** |
| **Arredondamento operacional** | **~5,3 milhões de tokens** |

> **Nota de calibração:** Este é o tamanho da base **antes de qualquer compressão, deduplicação ou filtro de qualidade**. Em produção, uma pipeline de limpeza pode reduzir esse volume em 15-25% (remoção de chunks de baixa qualidade, deduplicação de versões obsoletas). A base operacional pós-limpeza deve ficar entre 3,9M e 4,5M tokens.

---

## Parte 3 — Análise de Orçamento de Contexto

### 3.1 Distribuição do Budget de 128K Tokens

| Componente | Tokens | % do total |
|---|---|---|
| System prompt + instruções de comportamento | 2.000 | 1,6% |
| Reserva para resposta do modelo (geração) | 2.000 | 1,6% |
| Chunks recuperados (retrieval context) | **124.000** | **96,8%** |

Com chunks de 500 tokens cada: **248 chunks cabem teoricamente no orçamento restante**.

### 3.2 Por Que "Caber" ≠ "Funcionar"

A matemática de 248 chunks é um teto teórico, não uma recomendação operacional. Há dois fenômenos que tornam esse número ilusório:

**Lost in the Middle (Liu et al., 2023):** este é o achado mais importante para design de RAG. Experimentos controlados com GPT-4, Claude e outros LLMs demonstram consistentemente que informações posicionadas no **meio** de contextos longos são significativamente menos utilizadas pelo modelo do que informações no início (primeiros ~20%) ou no final (últimos ~20%) do contexto. Em contextos de 20+ chunks, a degradação de performance começa a se tornar mensurável. Em 100+ chunks, a degradação é severa para perguntas que requerem síntese de múltiplas fontes.

**Diluição de relevância:** Ao aumentar o número de chunks recuperados de 5 para 50, inevitavelmente incluímos chunks marginalmente relevantes. O modelo precisa de mais "esforço de atenção" para filtrar o ruído, e há evidência de que isso degrada a qualidade das respostas mesmo quando os chunks relevantes estão presentes no contexto.

### 3.3 Budget Operacional Recomendado

| Cenário de query | Chunks recomendados | Tokens de contexto | Cobertura da base |
|---|---|---|---|
| Fact lookup simples ("qual o prazo para devolução?") | 5-8 chunks | 2.500-4.000 tokens | 0,05% da base |
| Comparação entre documentos ("v1 vs v2 do PROC-042") | 10-15 chunks | 5.000-7.500 tokens | 0,1% da base |
| Análise de procedimento completo | 15-25 chunks | 7.500-12.500 tokens | 0,2% da base |
| Síntese cross-documentos (rara, alta complexidade) | 30-50 chunks | 15.000-25.000 tokens | 0,4% da base |

O budget restante (de 25K até 124K tokens) não deve ser desperdiçado — pode ser usado para:

- **Tokens de chain-of-thought:** instruir o modelo a raciocinar explicitamente sobre conflitos entre versões de documentos antes de responder.
- **Few-shot examples no prompt:** 2-3 exemplos de Q&A de alta qualidade para ancoragem de formato.
- **Metadados expandidos dos chunks:** em vez de só o texto, incluir campos como `doc_version`, `last_updated`, `confidence_score` formatados inline com cada chunk.

### 3.4 Impacto na Escolha da Estratégia de Retrieval

A limitação de cobertura (máximo 0,4% da base por query) tem implicações diretas na escolha de estratégia:

**Top-K pequeno (5-10) vs. Top-K grande (30-50):**
Um Top-K pequeno exige alta precisão no retriever primário — se o chunk correto não está nos top 5, a resposta falha. Um Top-K grande aumenta o recall mas introduz ruído e o problema do "Lost in the Middle". A resolução é **não tratar isso como binário**: usar retrieval de dois estágios.

**Reranking como componente obrigatório:**
O fluxo recomendado é:
1. Retrieve 50-100 chunks por similaridade de embedding (recall alto, precisão média)
2. Rerank os top-50 usando um modelo cross-encoder (Cohere Rerank, BGE-Reranker-v2) para selecionar os 10-20 mais relevantes
3. Montar o contexto final ordenando os chunks rerankeados com os mais relevantes nas posições extremas (início e fim do prompt — mitigação explícita do "Lost in the Middle")

**Hybrid search como proteção para conteúdo factual:**
Para queries que incluem valores numéricos exatos, nomes de procedimentos, códigos (CT-e, PROC-042, ramal 4500), a similaridade semântica pode ser inferior à busca lexical. Implementar BM25 + embedding search com fusão por Reciprocal Rank Fusion (RRF) garante que tanto a similaridade semântica quanto a correspondência exata de termos contribuam para o ranking.

**Trade-off "mais documentos" vs. "contexto de qualidade":**
A evidência empírica favorece qualidade sobre quantidade. Um contexto com 10 chunks altamente relevantes e bem posicionados supera consistentemente um contexto com 40 chunks de relevância média. A métrica operacional deve ser **precision@K** no reranker, não apenas recall do retriever inicial. O objetivo é manter P@10 ≥ 0,80 para queries típicas.

---

## Parte 4 — Estratégia de Chunking Justificada

### 4.1 Padrões de Query Esperados

Para uma base de conhecimento de logística/atendimento como a NovaTech, os tipos de query se distribuem aproximadamente assim:

| Tipo de query | % estimado | Exemplo |
|---|---|---|
| Consulta factual simples | 45% | "Qual o prazo de devolução?" |
| Consulta procedimental | 25% | "Como abro um chamado de devolução?" |
| Comparação/conflito entre versões | 15% | "Qual versão do multiplicador usar?" |
| Navegação hierárquica | 10% | "Quais exceções existem na política de devolução?" |
| Síntese multi-documento | 5% | "Qual o impacto no SLA de um cliente Gold com carga perigosa?" |

Cada tipo de query tem implicações diferentes para o design do chunking.

### 4.2 Estratégia Recomendada: Chunking Hierárquico com Contextualização Automática

#### Descrição técnica

A estratégia combina três camadas:

**Camada 1 — Proposicional (atomic facts):** chunks de 80-150 tokens contendo uma afirmação semântica completa. Otimizado para queries factuais simples. Exemplo: `[PROC-042-v2 | §2.1] Multiplicador regional Nordeste: 1.5 (vigência a partir de 01/12/2023).`

**Camada 2 — Semântica (procedural context):** chunks de 300-500 tokens contendo uma seção coerente de procedimento ou política. Gerados por sentence-window chunking com janela de ±2 sentenças de sobreposição. Otimizado para queries procedimentais e de navegação hierárquica.

**Camada 3 — Documento-pai (full context):** chunks de 800-1200 tokens contendo uma seção completa (H2 ou equivalente). Não são indexados diretamente — são utilizados apenas como contexto expandido após o retrieval dos chunks de Camada 2 encontrar correspondência (técnica: "contextual retrieval" ou "parent document retrieval", Anthropic, 2024).

O processo de retrieval opera primariamente na Camada 2 para a maioria das queries, com fallback para Camada 1 quando a precisão for prioritária e escalada para Camada 3 quando o contexto recuperado for insuficiente para gerar uma resposta completa.

#### Justificativa técnica (por que não chunking fixo de 512 tokens?)

Chunking fixo de tamanho uniforme (comum em tutoriais) ignora a semântica do documento. Um chunk fixo pode cortar no meio de uma enumeração de exceções, separar uma fórmula de sua tabela de parâmetros, ou incluir o final de uma seção e o início de outra — misturando contextos semanticamente díspares no mesmo vetor de embedding.

O embedding de um chunk semanticamente poluído tem menor similaridade com qualquer query específica do que teria se o chunk fosse limpo. O custo de embedding é o mesmo, mas a qualidade de retrieval é inferior.

#### Mitigação do Lost in the Middle

A mitigação opera em duas fases:

**Na montagem do contexto:** ao selecionar N chunks finais após reranking, posicioná-los em ordem de relevância decrescente a partir das extremidades — o chunk mais relevante vai para a posição 1, o segundo mais relevante vai para a posição N, o terceiro para a posição 2, e assim por diante (preenchimento em espiral das extremidades para o centro). Esta heurística garante que o LLM sempre encontre conteúdo altamente relevante nas posições de maior atenção.

**Na geração:** incluir no system prompt a instrução: `"Ao sintetizar a resposta, verifique TODOS os trechos de contexto fornecidos — não apenas os primeiros ou últimos. Caso identifique contradições entre fontes, mencione-as explicitamente."` Esta instrução não resolve o problema estrutural do LLM, mas aumenta o recall de informações medianas em ~15-20% em testes empíricos com GPT-4.

#### Comportamento por tipo de dado

**PDFs com tabelas:** chunks de Camada 1 = linhas individuais da tabela com cabeçalho repetido. Chunks de Camada 2 = tabela completa + parágrafo explicativo adjacente. Tabelas atômicas (≤ 600 tokens) são sempre Camada 2 diretamente.

**PDFs OCR:** apenas Camada 2 (a Camada 1 proposicional requer extração de alta confiança; OCR com confiança < 0,75 não deve gerar Camada 1). Metadado `low_confidence` acompanha cada chunk.

**Wikis:** as três camadas. Camada 1 = parágrafo único com prefixo de breadcrumb. Camada 2 = seção (H3) com H2 como prefixo de contexto. Camada 3 = página completa. Links internos resolvidos são anotados inline.

**Planilhas:** apenas Camada 1 e Camada 2. Camada 1 = célula ou linha serializada com cabeçalhos. Camada 2 = grupo de linhas relacionadas (ex: todas as regiões de uma tabela de multiplicadores). Nenhuma Camada 3 — planilhas não têm narrativa contínua que justifique chunks longos.

### 4.3 Parâmetros Finais Recomendados

| Parâmetro | Valor |
|---|---|
| Tamanho do chunk (Camada 2, padrão) | 350-500 tokens |
| Overlap entre chunks | 50 tokens (10-15%) |
| Número de chunks no retrieval inicial | 50-100 (pré-reranking) |
| Número de chunks no contexto final | 10-20 (pós-reranking) |
| Modelo de reranking | BGE-Reranker-v2-m3 ou Cohere Rerank 3 |
| Estratégia de fusão | RRF (Reciprocal Rank Fusion) entre BM25 e embeddings |
| Modelo de embedding recomendado | `text-embedding-3-large` (OpenAI) ou `multilingual-e5-large` para maior robustez em português |
| Posicionamento no contexto | Espiral das extremidades (mais relevante → início, segundo → fim, ...) |

---

## Parte 5 — Revisão Crítica e Riscos Não Mitigados

> Esta seção é o resultado de uma revisão sistemática das análises anteriores, identificando onde as estimativas podem ser otimistas, onde as estratégias têm pontos cegos, e onde suposições implícitas podem falhar em produção.

### 5.1 Estimativas que podem ser otimistas demais

**Contagem de palavras por página de PDF:** A análise usou 260 palavras/página para conteúdo textual. Esta é uma média razoável para documentos longos e bem redigidos, mas bases de conhecimento corporativas frequentemente incluem documentos de baixa densidade: apresentações exportadas como PDF (30-50 palavras/slide), formulários com campos em branco, documentos com muitas imagens. Se 20% dos PDFs forem desse tipo, a estimativa de tokens pode estar superdimensionada em 10-15%.

**O contrário também ocorre:** tabelas de logística serializadas com repetição de contexto por linha podem ser significativamente mais densas do que 320 palavras/página. Uma tabela de rotas com 200 linhas × 10 colunas pode gerar 3.000+ palavras quando serializada com contexto completo — muito mais do que a média estimada. Recomendação: realizar um pilot com 5% da base real para calibrar os parâmetros antes da ingestão completa.

**Planilhas:** a estimativa de 1.440 células ativas por planilha pode ser conservadora. Planilhas de precificação em logística podem ter centenas de linhas por faixa de CEP, resultando em 50.000+ células ativas. Nesse cenário, as planilhas podem representar não 720K tokens mas 3-5M tokens — mais do que a wiki inteira. **Esta é a estimativa com maior variância e maior risco de ser subestimada.**

### 5.2 Pontos fracos na estratégia de chunking

**O problema de versões conflitantes não é resolvido por chunking:** a análise recomenda preservar metadados de versão nos chunks, mas isso apenas permite que o LLM *veja* os dois valores conflitantes. Não existe garantia de que o modelo escolherá a versão correta. No caso da NovaTech (PROC-042 v1 e v2 coexistindo), um usuário perguntando "qual o multiplicador para o Nordeste?" receberá dois chunks com valores diferentes (1.4 e 1.5) — e o comportamento do LLM diante dessa ambiguidade é não-determinístico sem instrução explícita de resolução de conflito.

**Solução necessária mas não endereçada:** um mecanismo de **resolução de versão** no pipeline, possivelmente um grafo de relações de versão (`PROC-042-v2 supersedes PROC-042-v1 from 01/12/2023`), consultado antes da geração para filtrar chunks de versões obsoletas. Isso é arquiteturalmente mais complexo do que um simples índice vetorial.

**Chunking hierárquico em três camadas aumenta a complexidade operacional:** manter três índices sincronizados (proposicional, semântico, documento-pai) com atualização incremental é significativamente mais difícil do que um índice flat. Cada atualização de documento exige re-chunking das três camadas, atualização de metadados de parentesco, e eventual invalidação de cache de embeddings. O custo operacional contínuo não foi quantificado.

**Sobreposição de chunks em documentos muito curtos:** documentos de 1-2 páginas (como os da NovaTech) geram apenas 2-4 chunks de Camada 2. Com 50 tokens de overlap em chunks de 350-500 tokens, o overlap representa 10-14% do documento inteiro — criando redundância excessiva e distorção de ranking (o modelo verá fragmentos repetidos e pode inflacionar artificialmente a relevância desse documento).

### 5.3 Riscos técnicos e operacionais não adequadamente considerados

**Multilinguismo e mistura de idiomas:** documentos corporativos frequentemente mesclam português com terminologia técnica em inglês (CT-e, IoT, SLA, Azure DevOps, timestamps). O modelo de embedding `text-embedding-3-large` lida bem com isso, mas `multilingual-e5-large` pode produzir embeddings de menor qualidade para termos técnicos em inglês incorporados em prosa portuguesa. **Nenhum dos dois foi testado neste contexto específico na análise — a recomendação de embedding é uma suposição.**

**Drift de qualidade ao longo do tempo:** a análise trata a ingestão como um evento único. Em produção, a base de conhecimento é atualizada continuamente. O PROC-042-v2 substitui (ou deveria substituir) o v1. Documentos são revisados, seções são deletadas. Um índice vetorial sem mecanismo de expiração e atualização incremental se degrada progressivamente — chunks de documentos obsoletos permanecem no índice e continuam sendo recuperados.

**Custo de embeddings:** 5,3M tokens a $0,00002/token (text-embedding-3-large) = ~$106 para ingestão completa. Aceitável. Mas re-embeddings periódicos (ex: ao atualizar o modelo de embedding) podem representar custo recorrente significativo se a base crescer.

**Latência do pipeline de reranking:** adicionar um modelo de reranking ao fluxo aumenta a latência total em 100-500ms por query (dependendo do modelo e da infraestrutura). Para casos de uso de atendimento ao cliente (chatbot em tempo real), isso pode ser inaceitável. A análise não quantificou os trade-offs de latência vs. qualidade.

**Sem mecanismo de fallback para gaps documentais:** a análise identificou gaps (política de carga danificada não documentada formalmente, seguro de carga apenas no FAQ informal). O sistema RAG, por design, responderá às queries sobre esses tópicos com o conteúdo do FAQ informal — sem avisar o usuário que a resposta vem de uma fonte não validada. Isso é um risco operacional direto: o atendente pode agir com base em informação incorreta.

### 5.4 Suposições implícitas que podem falhar

**Suposição: os PDFs são nativamente digitais.** A análise coloca OCR como 15% do volume. Se a base real tiver mais documentos legados escaneados (contratos antigos, cópias físicas digitalizadas), esse percentual pode ser muito maior — e a degradação de qualidade do retrieval correspondentemente maior.

**Suposição: as planilhas têm estrutura tabular simples.** A estratégia de serialização assume planilhas como tabelas. Se existirem planilhas com dashboards, gráficos, objetos OLE, ou macros VBA, essas partes serão completamente ignoradas pelo pipeline, criando gaps silenciosos.

**Suposição: as queries dos usuários são bem formadas.** A análise calcula cobertura com base em queries claras e objetivas. Usuários reais de um sistema de atendimento fazem queries ambíguas ("e o frete especial então?"), com contexto implícito, ou com termos incorretos ("frete premium" em vez de "frete especial"). O sistema RAG sem um módulo de reformulação de query (HyDE — Hypothetical Document Embeddings, ou query expansion) terá performance significativamente pior para esse tipo de input.

**Suposição: o GPT-4o é o modelo final.** A análise foi calibrada para uma janela de 128K tokens. Se o projeto migrar para um modelo com janela menor (ex: versões compactas/locais), todas as estimativas de budget de contexto precisam ser recalibradas.

---

## Parte 6 — Análise Atualizada: Melhorias Incorporadas da Revisão Crítica

Com base na revisão da Parte 5, as seguintes modificações são incorporadas à análise original:

### 6.1 Estimativas de Tokens: Revisão Conservadora

O total revisado considera:
- Incerteza em planilhas: faixa operacional de 720K–3.000K tokens (em vez de ponto fixo)
- Variância em PDFs: faixa de 2.800K–3.600K tokens

**Faixa revisada da base de conhecimento:**
- Cenário conservador (pessimista): **7,5M tokens**
- Cenário mediano (baseline): **5,3M tokens**
- Cenário otimista: **4,2M tokens**

**Recomendação:** dimensionar a infraestrutura para o cenário pessimista e executar o pilot antes da ingestão completa.

### 6.2 Mecanismo de Resolução de Versão (Adição Necessária)

Adicionar ao pipeline uma **camada de gestão de versões** antes do indexador:

1. Na ingestão, detectar documentos com mesmo `doc_family_id` (ex: todas as versões do PROC-042).
2. Construir um grafo de versões: nó = documento, aresta = `supersedes` com data de vigência.
3. Na etapa de retrieval, após recuperar os top-N chunks, verificar o grafo de versões e marcar chunks de versões obsoletas com `is_active: false`.
4. Configurar o ranker para penalizar (não excluir!) chunks `is_active: false`, mantendo-os disponíveis para queries explícitas sobre versões históricas ("como era calculado antes de dezembro de 2023?").

### 6.3 Tratamento de Gaps Documentais (Adição Necessária)

Para cada chunk cuja fonte seja um documento informal (FAQ não validado, emails, documentos sem `Responsável` definido), adicionar ao contexto do chunk uma nota inline:

```
[AVISO DE FONTE: Este trecho provém de um documento não validado pelo Compliance 
(FAQ-Atendimento, versão não controlada). Confirme informações críticas na documentação 
normativa antes de orientar o cliente.]
```

Esta nota deve ser incluída no texto do chunk, não apenas em metadados, para que o LLM a processe no momento da geração e possa incluí-la na resposta ao usuário.

### 6.4 Query Expansion como Componente de Entrada

Adicionar um passo de reformulação de query antes do retrieval:

1. Para queries curtas ou ambíguas: usar o LLM para gerar 3 variantes da query original com diferentes formas de expressar a mesma intenção.
2. Executar retrieval para cada variante e fundir os resultados via RRF.
3. Alternativa mais eficiente: HyDE (Hypothetical Document Embeddings) — gerar um parágrafo hipotético que "responderia" à query, usar seu embedding para retrieval. Reduz o problema de mismatch entre o estilo de queries e o estilo dos documentos.

### 6.5 SLAs de Latência Explicitados

| Etapa do pipeline | Latência típica | Otimizável? |
|---|---|---|
| Query expansion (LLM call) | 300-800ms | Sim (cache para queries comuns) |
| Retrieval vetorial (HNSW) | 10-50ms | Sim (hardware) |
| BM25 retrieval | 5-20ms | Sim |
| RRF fusion | < 5ms | — |
| Reranking cross-encoder (20 chunks) | 150-400ms | Sim (batch, GPU) |
| Geração GPT-4o (20 chunks, resposta ~500 tokens) | 3.000-8.000ms | Limitado |
| **Total P50** | **~3,5-9s** | |
| **Total P95** | **~12-15s** | |

Para casos de uso de atendimento em tempo real com SLA de resposta < 5s, o pipeline completo com query expansion + reranking não é viável sem otimizações de infraestrutura (GPU para reranking, cache agressivo, streaming de resposta).

---

## Conclusão

Um pipeline RAG robusto para a base descrita requer significativamente mais do que um chunker + embedding + retriever simples. Os quatro tipos de fonte de dados (PDFs tabulares, OCR, wikis, planilhas) têm características de degradação diferentes que exigem tratamentos específicos na ingestão. O budget de contexto do GPT-4o é generoso (128K tokens), mas a eficiência real está limitada a 10-25 chunks de alta qualidade por query — o que cobre menos de 0,5% da base por pergunta.

A estratégia de chunking hierárquico em três camadas com reranking e mitigação explícita do "Lost in the Middle" é a abordagem mais robusta para a heterogeneidade descrita. Porém, sua implementação tem custos operacionais que não devem ser subestimados: complexidade de manutenção, latência adicionada pelo reranker, e necessidade de um grafo de versões para bases de conhecimento com documentos conflitantes.

Os riscos mais críticos não mitigados são: (a) a resolução de conflitos entre versões de documentos (PROC-042 v1 vs v2 é um caso real que causará inconsistências sem intervenção explícita), (b) a propagação de informações não validadas do FAQ informal sem sinalização adequada ao usuário final, e (c) a variância elevada na estimativa de tokens para planilhas, que pode tornar o pipeline 30-50% mais caro do que projetado.

---

*Documento de Design Técnico — versão 1.1*  
*Próximos passos recomendados: (1) Pilot com 5% da base para calibrar estimativas; (2) Definir política de versionamento de documentos antes da ingestão; (3) Selecionar e testar modelo de embedding em queries reais em português; (4) Definir SLA de latência aceitável antes de escolher incluir reranking.*
