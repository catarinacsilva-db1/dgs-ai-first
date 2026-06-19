import os
import glob
import re
import shutil
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# ---------------------------------------------------------------------------
# Mapeamento cidade → região para enriquecimento de chunks da PROC-042.
# Resolve o gap semântico entre queries com nome de cidade ("Manaus") e
# documentos que usam apenas denominação regional ("Norte").
# ---------------------------------------------------------------------------
REGIOES_CIDADES = {
    "Norte":         "Manaus, Belém, Porto Velho, Macapá, Boa Vista, Rio Branco, Palmas",
    "Nordeste":      "Salvador, Recife, Fortaleza, Natal, João Pessoa, Maceió, Aracaju, Teresina, São Luís",
    "Centro-Oeste":  "Brasília, Goiânia, Campo Grande, Cuiabá",
    "Sudeste":       "São Paulo, Rio de Janeiro, Belo Horizonte, Vitória, Campinas",
    "Sul":           "Curitiba, Porto Alegre, Florianópolis",
}


def extrair_metadados(file_path: str) -> dict | None:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        source = os.path.basename(file_path)
        doc_id = os.path.splitext(source)[0]

        versao_match = re.search(r"\*\*Versão:\*\*\s*(.+)", content)
        versao = versao_match.group(1).strip() if versao_match else "0.0"

        data_match = re.search(r"\*\*(?:Data de emissão|Última atualização):\*\*\s*(.+)", content)
        data_emissao = data_match.group(1).strip() if data_match else "Não informada"

        resp_match = re.search(r"\*\*Responsável:\*\*\s*(.+)", content)
        responsavel = resp_match.group(1).strip() if resp_match else "Não informado"

        base_id_match = re.match(r"^([A-Z]+-\d+)", doc_id)
        base_id = base_id_match.group(1) if base_id_match else doc_id.split("-")[0]

        return {
            "source":      source,
            "doc_id":      doc_id,
            "versao":      versao,
            "data_emissao": data_emissao,
            "responsavel": responsavel,
            "base_id":     base_id,
            "file_path":   file_path,
            "content":     content,
        }
    except Exception as e:
        print(f"[ERRO] Falha ao ler metadados de {file_path}: {e}")
        return None


def obter_versao_tupla(versao_str: str) -> tuple:
    numeros = re.findall(r"\d+", versao_str)
    return tuple(map(int, numeros)) if numeros else (0,)


def enriquecer_geograficamente(texto: str) -> str:
    """
    Detecta regiões geográficas em linhas de tabela (padrão "| Região |") e
    adiciona as principais cidades de cada região ao final do chunk.

    Por que: o modelo de embedding não conecta "Manaus" à "região Norte"
    porque os documentos PROC-042 usam apenas denominações regionais.
    Ao acrescentar os nomes de cidade, o embedding do chunk passa a incluir
    essas referências geográficas e a query "frete para Manaus" encontra
    o chunk de multiplicadores com score significativamente maior.
    """
    regioes_encontradas = [
        regiao for regiao in REGIOES_CIDADES
        if re.search(rf"\|\s*{regiao}\s*\|", texto)
    ]
    if not regioes_encontradas:
        return texto

    linhas = ["\nCidades atendidas por região:"]
    for regiao in regioes_encontradas:
        linhas.append(f"- {regiao}: {REGIOES_CIDADES[regiao]}")
    return texto + "\n".join(linhas)


def enriquecer_tabelas(texto: str) -> str:
    """
    Detecta a primeira tabela markdown e acrescenta versão narrativa dos dados.

    Por que: modelos de embedding têm representação fraca de células em formato
    | col | val |. Texto narrativo ("Gold: Até 2h úteis") conecta melhor com
    queries em linguagem natural como "Qual o SLA do cliente Gold?".
    Também melhora a PROC-042: "Norte — Multiplicador: 1.8" reforça o sinal
    geográfico combinado com o enriquecimento de cidades.
    """
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


def chunkar_por_headers(content: str, doc_meta: dict) -> list[Document]:
    """
    Estratégia de chunking estrutural: divide o documento pelos cabeçalhos
    markdown ## (seção) e ### (subseção).

    Por que substituir RecursiveCharacterTextSplitter(size=500):
    - O splitter por caractere corta seções no meio (ex: a lista de cargas
      perigosas da seção 3.2 era entregue apenas com o cabeçalho, sem conteúdo).
    - Os documentos NovaTech já estão estruturados em subseções semânticas
      coesas (3.1 prazo, 3.2 exceções, 3.3 procedimento, cada item do FAQ).
      Respeitar essa estrutura garante que cada chunk seja uma unidade
      respondível por si só — exatamente o que o Anexo B define como chunk ideal.

    strip_headers=False preserva o título da seção no texto do chunk, o que
    melhora o embedding porque o cabeçalho carrega vocabulário relevante
    (ex: "Prazo geral", "Exceções", "Multiplicadores regionais").

    Fallback: seções > 800 chars (raras nesta base) recebem um segundo
    split por parágrafo com overlap de 150 chars para manter contexto.
    """
    headers_to_split_on = [
        ("#",   "titulo"),
        ("##",  "secao"),
        ("###", "subsecao"),
    ]

    try:
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )
    except TypeError:
        # Versões antigas do LangChain não têm strip_headers
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
        )

    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],
    )

    raw_chunks = md_splitter.split_text(content)
    documents = []

    for hchunk in raw_chunks:
        text = hchunk.page_content.strip()
        if not text or len(text) < 30:
            continue

        # subsecao tem prioridade: "3.1. Prazo geral" é mais específico que "3. Regras"
        subsecao = hchunk.metadata.get("subsecao", "")
        secao    = hchunk.metadata.get("secao", "")
        section_label = subsecao or secao or "—"
        chunk_tipo = "subsecao" if subsecao else "secao"

        # Enriquecimento geográfico: apenas em chunks de PROC-042 com tabela regional
        if "PROC-042" in doc_meta["source"]:
            text = enriquecer_geograficamente(text)

        # Enriquecimento de tabelas: converte markdown table para texto narrativo
        # Aplicado a todos os chunks — resolve embedding fraco de células | col | val |
        text = enriquecer_tabelas(text)

        metadata = {
            "source":      doc_meta["source"],
            "doc_id":      doc_meta["doc_id"],
            "versao":      doc_meta["versao"],
            "data_emissao": doc_meta["data_emissao"],
            "responsavel": doc_meta["responsavel"],
            "base_id":     doc_meta["base_id"],
            "is_latest":   doc_meta.get("is_latest", "true"),
            "secao":       section_label,
            "chunk_tipo":  chunk_tipo,
        }

        if len(text) <= 1200:
            documents.append(Document(page_content=text, metadata=metadata))
        else:
            # Fallback para seções muito longas (acima de 1200 chars após enriquecimento)
            # Enrichments já foram aplicados ao texto completo antes do split
            for j, sub in enumerate(fallback_splitter.split_text(text)):
                sub = sub.strip()
                if sub:
                    m = {**metadata, "secao": f"{section_label} (parte {j + 1})"}
                    documents.append(Document(page_content=sub, metadata=m))

    return documents


def main():
    print("Iniciando processo de indexação de documentos (RAG NovaTech)...\n")

    md_dir    = input("Digite o caminho da pasta onde estão os arquivos .md: ").strip()
    chroma_dir = input("Digite o caminho da pasta do ChromaDB (padrão: ./chroma_db): ").strip()
    if not chroma_dir:
        chroma_dir = "./chroma_db"

    forcar_str = input("Forçar reindexação completa (apaga o banco atual)? [s/N]: ").strip().lower()
    forcar_reindex = forcar_str == "s"

    print("\nInicializando configurações...")

    md_files = glob.glob(os.path.join(md_dir, "*.md"))
    if not md_files:
        print(f"[ERRO] Nenhum arquivo .md encontrado em: {md_dir}")
        return

    parsed_docs = []
    for fp in md_files:
        meta = extrair_metadados(fp)
        if meta:
            parsed_docs.append(meta)

    # ------------------------------------------------------------------
    # Resolução de versões: AMBAS as versões são indexadas.
    #
    # Por que não descartar a versão antiga:
    # - Os documentos PROC-042 v1 e v2 coexistem no sistema real (Anexo A).
    # - O Anexo B prevê explicitamente que PROC-042-B (v1) pode aparecer
    #   nos resultados — o pipeline deve testar o cenário de contradição.
    # - A instrução 3 do prompt-sistema já orienta o LLM a priorizar a
    #   versão mais recente quando houver divergência.
    # - O campo is_latest="false" sinaliza para o retriever/prompt_builder
    #   que o chunk é de versão anterior.
    # ------------------------------------------------------------------
    grouped: dict[str, list] = {}
    for doc in parsed_docs:
        grouped.setdefault(doc["base_id"], []).append(doc)

    for base_id, group in grouped.items():
        group.sort(key=lambda x: obter_versao_tupla(x["versao"]), reverse=True)
        group[0]["is_latest"] = "true"
        for old_doc in group[1:]:
            old_doc["is_latest"] = "false"
            print(
                f"[AVISO] {old_doc['source']} (v{old_doc['versao']}) é versão anterior a "
                f"{group[0]['source']} (v{group[0]['versao']}). "
                f"Ambas serão indexadas; o LLM prioriza a mais recente via prompt."
            )

    # Inicializa embeddings
    print(f"\nCarregando modelo de embeddings 'all-MiniLM-L6-v2'...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # Remove banco anterior se reindexação forçada
    if forcar_reindex and os.path.exists(chroma_dir):
        shutil.rmtree(chroma_dir)
        print(f"[INFO] Banco ChromaDB em '{chroma_dir}' removido para reindexação completa.")

    vectorstore = Chroma(
        collection_name="novatech_docs",
        embedding_function=embeddings,
        persist_directory=chroma_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )

    skipped   = 0
    processed = 0
    total_chunks_gerados = 0

    for doc in parsed_docs:
        # Reprocessamento incremental: pula se já indexado (a menos que --force)
        if not forcar_reindex:
            existing = vectorstore.get(where={"source": doc["source"]})
            if existing.get("ids"):
                print(f"[SKIP] {doc['source']} já indexado.")
                skipped += 1
                continue

        try:
            chunks = chunkar_por_headers(doc["content"], doc)

            if not chunks:
                print(f"[AVISO] {doc['source']} não gerou chunks — verifique a estrutura do arquivo.")
                continue

            n = len(chunks)
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"]  = i
                chunk.metadata["total_chunks"] = n

            ids = [f"{doc['doc_id']}_chunk_{i}" for i in range(n)]
            vectorstore.add_documents(documents=chunks, ids=ids)

            processed += 1
            total_chunks_gerados += n
            versao_label = f"v{doc['versao']}" if doc['versao'] != "Não controlada" else "não controlada"
            latest_label = "" if doc.get("is_latest") == "true" else " [versão anterior]"
            print(f"[INDEXADO] {doc['source']} ({versao_label}{latest_label}) → {n} chunks")

        except Exception as e:
            print(f"[ERRO] Falha ao processar {doc['source']}: {e}")

    try:
        total_no_banco = len(vectorstore.get().get("ids", []))
    except Exception:
        total_no_banco = "Desconhecido"

    print("\n========== RESUMO DA INDEXAÇÃO ==========")
    print(f"Arquivos processados       : {processed}")
    print(f"Arquivos pulados (já exist): {skipped}")
    print(f"Chunks gerados nesta execução: {total_chunks_gerados}")
    print(f"Total de chunks no banco   : {total_no_banco}")
    print(f"Coleção ChromaDB           : novatech_docs")
    print(f"Pasta do banco             : {chroma_dir}")
    print("=========================================")


if __name__ == "__main__":
    main()
