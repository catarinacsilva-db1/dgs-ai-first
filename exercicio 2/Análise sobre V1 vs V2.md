---
#Análise sobre respostas

O primeiro prompt criado trouxe respostas satisfatórias, mas podem ser melhoradas. O V1 incialmente já trouxe a lista de documentos e de início já identificou conflito entre as versões de arquivo e aplicou a regra de priorizar o documento mais recente. Porém, já trazia essas informações sem ser solicitado e com fontes inline. No V2, o assistente é mais humanizado, identificou a possibilidade do Atendente estar em treinamento e fez recomendações com base nisso, traz fonte ao final da citação.
Primeira pergunta: Qual o prazo de devolução para carga perigosa?
	-V1: Não caiu na pegadinha, trouxe a resposta correta mas com pouca elaboração sobre a negativa.
	-V2: Também não caiu na pegadinha, retornou a classificação das cargas consideradas perigosas, com uma resposta melhor estruturada com maior possibilidade de entendimento por um humano. Trouxe um detalhamento justificando e um ponto de atenção voltado a pergunta. 

Segunda pergunta: Meu cliente é Gold, qual o SLA de resolução?
	-V1: trouxe informações demais e mal estruturadas. Respondeu corretamente, mas o fluxo da resposta está estranho.
	-V2: Trouxe as informações solicitadas, trouxe informações também sobre o SLA de resposta. São as mesmas informações do V1, mas de forma mais clara e direta. Trouxe como pontos de atenção o conceito de incidente crítico. Parece um local mais adequado para essa informação.

Terceira pergunta: Quanto custa o frete para 600kg para Manaus?
	-V1: Acertou que não é possível calcular e retornou a fórmula, mas inventou que o dado necessário estava em documento externo
	-V2: Também retornou a resposta correta com a fómula, e diferente do V1 apenas informou que não está disponível nessa documentação. Trouxe informações mais objetivas.