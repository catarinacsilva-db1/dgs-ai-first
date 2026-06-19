from langchain_chroma import Chroma


def buscar_chunks(
    pergunta: str,
    vectorstore: Chroma,
    n: int = 5,
    score_minimo: float = 0.35,
    filtro_metadados: dict | None = None
) -> list[dict]:
    """
    Busca os chunks mais similares a uma pergunta no vectorstore do Chroma.

    :param pergunta: A query em formato de string.
    :param vectorstore: Instância do ChromaDB já inicializada.
    :param n: Número base de chunks a serem retornados.
    :param score_minimo: Limiar mínimo de score de relevância.
                        Definido em 0.35 — modelo all-MiniLM-L6-v2 (inglês) gera scores
                        uniformemente baixos para documentos em português; 0.40 eliminava
                        chunks obrigatórios como SLA-2024-B (P3) que chegavam a ~0.36.
    :param filtro_metadados: Dicionário opcional com filtros para a busca no ChromaDB.
    :return: Lista de dicionários contendo os chunks, metadados e scores.
    """

    # 1. Buscar os chunks mais similares no vectorstore (solicitando n * 2 resultados)
    try:
        raw_results = vectorstore.similarity_search_with_relevance_scores(
            query=pergunta,
            k=n * 3,
            filter=filtro_metadados
        )
    except Exception as e:
        raise RuntimeError(f"[RETRIEVER] Erro de conexão ou falha ao buscar no ChromaDB: {e}")

    # 3. Ordenar sempre por score decrescente
    raw_results.sort(key=lambda x: x[1], reverse=True)

    # Separar os que passam no filtro dos que ficam abaixo do score
    valid_results = []
    below_threshold = []

    for doc, score in raw_results:
        # Conversão explícita para float garantindo consistência
        score_f = float(score)
        if score_f >= score_minimo:
            valid_results.append((doc, score_f, False))
        else:
            below_threshold.append((doc, score_f, True))

    # 6. Se nenhum chunk atingir o score mínimo
    if not valid_results:
        print("[RETRIEVER] Nenhum chunk relevante encontrado para a pergunta.")
        return []

    # Recorta para a quantidade desejada 'n'
    final_docs = valid_results[:n]

    # Pad removido: injetar chunks abaixo do limiar causava ruído no contexto do LLM
    # (ex: FAQ-22 sobre seguro e FAQ-38 sobre carga danificada sendo enviados para a
    # pergunta "Posso devolver carga perigosa?"). Quando não há chunks suficientemente
    # relevantes, é mais correto retornar contexto vazio e deixar o prompt-sistema
    # acionar a resposta "Não encontrei essa informação nos documentos disponíveis."

    # Construir o retorno de objetos no formato lista de dicionários
    formatted_results = []
    for rank, (doc, score, is_below) in enumerate(final_docs):
        metadata = doc.metadata or {}
        
        # Mapeamento estrito solicitado
        item = {
            "chunk_index_global": rank,
            "score": score,
            "texto": doc.page_content,
            "source": metadata.get("source", ""),
            "doc_id": metadata.get("doc_id", ""),
            "versao": str(metadata.get("versao", "")),
            "data_emissao": metadata.get("data_emissao", ""),
            "responsavel": metadata.get("responsavel", ""),
            "base_id": metadata.get("base_id", ""),
            "is_latest": metadata.get("is_latest", "true"),
            "secao": metadata.get("secao", ""),
            "chunk_index": int(metadata.get("chunk_index", 0)),
            "total_chunks": int(metadata.get("total_chunks", 0)),
            "abaixo_do_limiar": is_below
        }
        formatted_results.append(item)

    return formatted_results


# =====================================================================
# EXEMPLO DE USO
# =====================================================================
# if __name__ == "__main__":
#     # Setup básico / importando apenas para simular a chamada da pipeline
#     # Supondo que a indexação já foi executada:
#     
#     embeddings_model = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
#     
#     db = Chroma(
#         collection_name="novatech_docs", 
#         persist_directory="./chroma_db", 
#         embedding_function=embeddings_model
#     )
#     
#     pergunta_teste = "Qual a regra para os fretes especiais pesados?"
#     
#     # Exemplo 1: Sem filtro de metadados
#     print("=== EXEMPLO 1: BUSCA SEM FILTRO ===")
#     resultados = buscar_chunks(
#         pergunta=pergunta_teste,
#         vectorstore=db,
#         embedding_model=embeddings_model,
#         n=5,
#         score_minimo=0.30
#     )
#     for res in resultados:
#         print(f"Rank {res['chunk_index_global']} | Score: {res['score']:.4f} | Abaixo limiar? {res['abaixo_do_limiar']}")
#         print(f"Fonte: {res['source']} (Versão: {res['versao']})")
#         print(f"Trecho: {res['texto'][:80]}...")
#         print("-" * 40)
#
#     # Exemplo 2: Com filtro de metadados
#     print("\n=== EXEMPLO 2: BUSCA COM FILTRO (Diretoria Comercial) ===")
#     resultados_com_filtro = buscar_chunks(
#         pergunta=pergunta_teste,
#         vectorstore=db,
#         embedding_model=embeddings_model,
#         n=3,
#         score_minimo=0.30,
#         filtro_metadados={"responsavel": "Diretoria Comercial"}
#     )
#     for res in resultados_com_filtro:
#         print(f"Rank {res['chunk_index_global']} | Score: {res['score']:.4f} | Abaixo limiar? {res['abaixo_do_limiar']}")
#         print(f"Fonte: {res['source']} (Responsável: {res['responsavel']})")
#         print(f"Trecho: {res['texto'][:80]}...")
#         print("-" * 40)
