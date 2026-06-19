import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Ajuste os imports para pegar as funções dos seus arquivos
from retriever import buscar_chunks
from prompt_builder import montar_prompt

def main():
    # Caminho do ChromaDB
    chroma_dir = "./chroma_db"
    
    if not os.path.exists(chroma_dir):
        print(f"Erro: Dir {chroma_dir} não encontrado. Execute indexar_documentos.py primeiro.")
        return

    # 1. Carregar modelo e DB
    print("Carregando embeddings e conectando ao ChromaDB...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(
        collection_name="novatech_docs",
        embedding_function=embeddings,
        persist_directory=chroma_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )

    # Pegar 5 perguntas do mapa de cobertura do Anexo B
    perguntas = [
        "Qual o prazo de devolução?",
        "Posso devolver carga perigosa?",
        "Qual o SLA do cliente Gold?",
        "Frete para 600kg para Manaus?",
        "Carga perigosa com frete expresso?"
    ]

    print("\n" + "="*50)
    print("INICIANDO PIPELINE RAG")
    print("="*50)

    # Limpar/Criar pasta de output dos prompts (Item 3)
    if not os.path.exists("prompts_gerados"):
        os.makedirs("prompts_gerados")

    for i, pergunta in enumerate(perguntas, start=1):
        print(f"\n--- PERGUNTA {i} ---")
        print(f"Q: '{pergunta}'")
        
        # O Item 2 pede para documentar os chunks recuperados e o score.
        chunks_recuperados = buscar_chunks(
            pergunta=pergunta,
            vectorstore=vectorstore,
            n=5,          # busca até 5 candidatos (internamente n*3=15 são avaliados)
            score_minimo=0.35
        )
        
        # Logar dados para documentação 
        if not chunks_recuperados:
            print("Resultado: Nenhum chunk recuperado para esta pergunta (tudo abaixo do limiar ou nulo).")
        else:
            print("Chunks Recuperados (Ordene e compare com o Anexo B para relatar o gabarito):")
            for c in chunks_recuperados:
                source = c['source']
                score = c['score']
                abaixo = c['abaixo_do_limiar']
                # Retirando um preview de 60 chars para ajudar
                preview = c['texto'][:80].replace("\n", " ") + "..."
                print(f"  -> Score {score:.3f} | Arquivo: {source} (Abaixo limiar? {abaixo})")
                print(f"     Trecho: {preview}")

        # Montar o prompt formatado
        prompt_final = montar_prompt(pergunta, chunks_recuperados)
        
        # Salva o prompt final para o Item 3
        prompt_filename = f"prompts_gerados/prompt_pergunta_{i}.txt"
        with open(prompt_filename, "w", encoding="utf-8") as f:
            f.write(prompt_final)
            
        print(f"\n[!] Prompt montado e salvo em: {prompt_filename}")
        print("    -> Copie o conteúdo desse arquivo e cole no Claude (para concluir o Item 3).")

if __name__ == "__main__":
    main()
