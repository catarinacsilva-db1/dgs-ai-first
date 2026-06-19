from typing import List, Dict

SYSTEM_PROMPT = """Você é um assistente especializado em políticas, procedimentos e SLAs da NovaTech.

Suas instruções obrigatórias são:
1. Responda APENAS com base nos documentos fornecidos na seção <documentos>. Nunca invente informações e nunca extrapole além do que está explicitamente presente nos trechos.
2. Sempre indique a fonte (Fonte e Versão) correspondente ao responder.
3. Se houver trechos de versões diferentes do mesmo documento fornecidos no contexto, priorize explicitamente a versão mais recente em sua resposta e avise o usuário sobre a divergência encontrada.
4. Se a resposta para a pergunta não estiver presente nos chunks de texto, responda exatamente com a frase: "Não encontrei essa informação nos documentos disponíveis. Consulte [responsavel] para mais detalhes." (substitua "[responsavel]" pelo cargo/setor relacionado se for possível deduzir do contexto, ou mantenha a palavra caso contrário)."""


def montar_prompt(
    pergunta: str,
    chunks: list[dict],
    max_tokens_contexto: int = 3000,
    incluir_aviso_limiar: bool = True
) -> str:
    """
    Monta o prompt estruturado com tags XML para o modelo Claude.
    
    :param pergunta: A pergunta do usuário.
    :param chunks: Lista de chunks recuperados do ChromaDB (dicionários).
    :param max_tokens_contexto: Limite de tokens estimado para a seção de documentos.
    :param incluir_aviso_limiar: Indica se deve incluir alerta sobre chunks de baixa similaridade.
    :return: String contendo o prompt final montado.
    """
    if not chunks:
        contexto_str = "[SEM CONTEXTO] Nenhum documento relevante foi recuperado para esta pergunta."
    else:
        blocos_contexto = []
        tokens_acumulados = 0
        teve_chunk_low_score = False
        chunks_incluidos = 0

        for chunk in chunks:
            abaixo_limiar = chunk.get("abaixo_do_limiar", False)
            if abaixo_limiar:
                teve_chunk_low_score = True
                
            aviso_limiar_str = "\n[ATENÇÃO: relevância abaixo do limiar mínimo]" if abaixo_limiar else ""

            # Sinaliza versão anterior para acionar a instrução 3 do system prompt
            is_latest = chunk.get("is_latest", "true")
            aviso_versao_str = "\n[VERSÃO ANTERIOR — priorize a versão mais recente do mesmo documento]" if is_latest == "false" else ""

            bloco_doc = (
                f"--- Documento [{chunk.get('chunk_index_global', 0) + 1}] ---\n"
                f"Fonte     : {chunk.get('source', '')}\n"
                f"Versão    : {chunk.get('versao', '')}\n"
                f"Emissão   : {chunk.get('data_emissao', '')}\n"
                f"Responsável: {chunk.get('responsavel', '')}\n"
                f"Score     : {chunk.get('score', 0.0):.2f}{aviso_limiar_str}{aviso_versao_str}\n\n"
                f"{chunk.get('texto', '')}\n"
                f"--- Fim do Documento [{chunk.get('chunk_index_global', 0) + 1}] ---\n"
            )
            
            # Estimativa simples: 1 token representam aproximadamente 4 caracteres
            estimativa_tokens = len(bloco_doc) // 4
            
            if tokens_acumulados + estimativa_tokens > max_tokens_contexto:
                print(f"[PROMPT_BUILDER] Contexto truncado: {chunks_incluidos} de {len(chunks)} chunks incluídos por limite de tokens.")
                break
                
            blocos_contexto.append(bloco_doc)
            tokens_acumulados += estimativa_tokens
            chunks_incluidos += 1

        contexto_final_linhas = []
        if incluir_aviso_limiar and teve_chunk_low_score:
            contexto_final_linhas.append("[NOTA: Um ou mais trechos abaixo possuem relevância baixa. Use-os com cautela.]\n")
            
        contexto_final_linhas.extend(blocos_contexto)
        contexto_str = "\n".join(contexto_final_linhas).strip()

    prompt = (
        f"<system>\n"
        f"{SYSTEM_PROMPT}\n"
        f"</system>\n\n"
        f"<documentos>\n"
        f"{contexto_str}\n"
        f"</documentos>\n\n"
        f"<pergunta>\n"
        f"{pergunta}\n"
        f"</pergunta>"
    )

    return prompt

# =====================================================================
# EXEMPLO DE USO
# =====================================================================
# if __name__ == "__main__":
#     chunks_simulados = [
#         {
#             "chunk_index_global": 0,
#             "score": 0.85,
#             "texto": "Cargas acima de 5.000kg requerem aprovação prévia do gerente de operações regional.",
#             "source": "PROC-042-v2-frete-especial-revisado.md",
#             "doc_id": "PROC-042-v2",
#             "versao": "2.0",
#             "data_emissao": "10/11/2023",
#             "responsavel": "Diretoria Comercial",
#             "chunk_index": 2,
#             "total_chunks": 5,
#             "abaixo_do_limiar": False
#         },
#         {
#             "chunk_index_global": 1,
#             "score": 0.25,
#             "texto": "O frete para produtos químicos perigosos custará adicional de 0,8%.",
#             "source": "POL-001-politica-devolucao.md",
#             "doc_id": "POL-001",
#             "versao": "3.1",
#             "data_emissao": "15/01/2024",
#             "responsavel": "Diretoria de Operações",
#             "chunk_index": 0,
#             "total_chunks": 3,
#             "abaixo_do_limiar": True
#         }
#     ]
#     
#     pergunta_teste = "Qual a restrição para fretes acima de cinco mil quilos?"
#     
#     prompt_gerado = montar_prompt(
#         pergunta=pergunta_teste, 
#         chunks=chunks_simulados, 
#         max_tokens_contexto=3000
#     )
#     
#     print(prompt_gerado)
