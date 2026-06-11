Você é um especialista em arquitetura de sistemas de RAG (Retrieval-Augmented Generation) com profundo conhecimento em gestão de contexto de LLMs, processamento de diferentes tipos de documentos e otimização de custos de tokens.

Sua tarefa é produzir uma análise técnica detalhada e crítica sobre como implementar um pipeline de RAG robusto para uma base de conhecimento heterogênea. Esta análise servirá como documento de design para tomadas de decisão técnicas.

## Análise por Tipo de Fonte de Dados

Para cada um dos seguintes tipos de fonte, você deve cobrir OBRIGATORIAMENTE:

1. **PDFs com tabelas**
2. **PDFs escaneados (OCR)**
3. **Wikis com links e estrutura hierárquica**
4. **Planilhas com fórmulas e dependências**

Para cada tipo, estruture sua resposta assim:
- **Desafio técnico para o pipeline RAG**: o que torna difícil extrair e indexar este tipo de dado? Que perda de informação ocorre?
- **Impacto na qualidade das respostas**: como esses desafios degradam a relevância, precisão ou utilidade das respostas ao usuário final?
- **Estratégia de tratamento recomendada**: que abordagens técnicas (parsing, normalização, chunking, metadata extraction) mitigam esses problemas?

## Estimativa do Tamanho da Base em Tokens

Calcule o tamanho aproximado da base de conhecimento usando estes dados:
- ~800 documentos PDF com média de 10 páginas cada
- ~400 páginas de conteúdo wiki com média de 1.500 palavras cada
- ~50 planilhas

Use a regra prática de **0.75 palavras por token** para suas estimativas.

Seu cálculo deve deixar explícito:
- Tokens para PDFs (separar: conteúdo textual vs. tabelas vs. OCR)
- Tokens para wiki
- Tokens para planilhas
- Total estimado com margem de segurança (5-10%)

## Análise de Orçamento de Contexto

Considerando os seguintes parâmetros:
- **Modelo**: GPT-4o com 128K tokens de janela de contexto
- **Overhead fixo**: system prompt + instruções consomem ~2.000 tokens
- **Tamanho de chunk padrão**: ~500 tokens por chunk

Você deve calcular e discutir:
- Quantos chunks cabem no orçamento restante por query?
- Qual o impacto dessa limitação na cobertura do conhecimento por pergunta?
- Como esse orçamento afeta a escolha entre estratégias de retrieval (top-K pequeno vs. grande, reranking, hybrid search)?
- Quais trade-offs emergem entre recuperar "mais documentos" vs. "contexto de qualidade melhor"?

## Estratégia de Chunking Justificada

Recomende uma estratégia de chunking que considere:
- **Padrão de perguntas**: que tipos de perguntas você espera que os usuários façam? (ex: consultas simples de fato, comparações entre documentos, análises de tabelas, navegação em estruturas hierárquicas)
- **Problema do "Lost in the Middle"**: pesquisas mostram que informações no meio de contextos longos são frequentemente ignoradas pelos LLMs. Como sua estratégia de chunking e ordenação mitiga isso?
- **Heterogeneidade dos dados**: por que sua recomendação funciona bem para PDFs com tabelas, OCR, wikis e planilhas simultaneamente (ou se não funciona, o que muda por tipo)?

Justifique sua recomendação com evidência técnica, não apenas com boas práticas genéricas.

## Revisão Crítica de Sua Própria Análise

Após completar a análise acima, você deve:

1. **Revisar sua própria análise** identificando:
   - Estimativas que podem ser otimistas demais (onde você pode ter subestimado complexidade ou tamanho)?
   - Pontos fracos em sua estratégia de chunking?
   - Riscos técnicos ou operacionais que você não considerou adequadamente?
   - Suposições não explícitas que poderiam falhar na prática?

2. **Documentar o feedback crítico** em uma seção separada chamada "Revisão Crítica e Riscos Não Mitigados"

3. **Atualizar sua análise original** incorporando os pontos de melhoria identificados na revisão.

## Critérios de Qualidade

Sua análise deve ser:
- **Tecnicamente precisa**: use termos corretos, cite conceitos estabelecidos (lost in the middle, token budgets, retrieval strategies)
- **Crítica e realista**: não evite mencionar limitações, trade-offs ou cenários onde sua recomendação pode falhar
- **Justificada**: cada recomendação deve ter fundamento técnico claro, não ser genérica
- **Prática**: as recomendações devem ser implementáveis, com métricas e decisões concretas

Estruture o documento de forma clara e legível, com seções bem delimitadas e conclusões resumidas.