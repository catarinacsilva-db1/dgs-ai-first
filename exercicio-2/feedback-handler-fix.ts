import { app, HttpRequest, HttpResponseInit } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import { z } from 'zod';

// 10. Validação de existência da variável de ambiente (Fail-fast)
const cosmosConnectionString = process.env.COSMOS_CONNECTION_STRING;
if (!cosmosConnectionString) {
  throw new Error('COSMOS_CONNECTION_STRING environment variable is required');
}

// 5. Instância singleton do CosmosClient reutilizada em todas as requisições
// 8. Utilização do import padronizado em vez de require inline
const client = new CosmosClient(cosmosConnectionString);
const database = client.database('novatech');
const container = database.container('feedbacks');

// 1. Zod Schema para validação garantida do input
const feedbackSchema = z.object({
  queryId: z.string().min(1, 'queryId é obrigatório'),
  rating: z.number().int().min(1).max(5, 'Rating deve estar entre 1 e 5'),
  comment: z.string().optional(),
  attendantEmail: z.string().email('Formato de email inválido')
});

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  try { // 3. Try/catch envolvendo toda a execução para não expor a stack e tratar os erros corretamente
    const rawBody = await request.json();

    // 1. Aplicação e verificação da validação
    const validationResult = feedbackSchema.safeParse(rawBody);
    if (!validationResult.success) {
      return {
        status: 400,
        jsonBody: {
          error: 'Bad Request: Validação de corpo falou.',
          details: validationResult.error.format()
        }
      };
    }

    const { queryId, rating, comment, attendantEmail } = validationResult.data;

    const feedback = {
      // 9 e 11. Geração de um "id" idempotente para evitar duplicações e partition key
      id: `${queryId}-${attendantEmail}`,
      partitionKey: queryId, 
      queryId,
      rating,
      comment,
      attendantEmail,
      timestamp: new Date().toISOString()
    };

    // 2. Logando apena informações essenciais que não vazam PII sensíveis do atendimento/attendantEmail.
    console.log(`Recebendo Feedback validado de rating: ${rating} | queryId: ${queryId}`);

    // 6 e 9. Utilização do "upsert" visando tratamento idempotente com try internos pelo CosmosClient (que possui mecanismo de retries e backoff base no sdk).
    await container.items.upsert(feedback);

    // 7. Retorno devidamente estruturado em json.
    return {
      status: 200,
      jsonBody: { message: 'Feedback processado de forma segura e bem sucedida com o sistema!' }
    };

  } catch (error: any) {
    // 3. Captura global para exceptions não esperadas (timeout, erros de banco, 429) e gerando logs adequados.
    console.error('Falha interna ao realizar a operação de feedback:', error.message);
    
    return {
      status: 500,
      jsonBody: {
        error: 'Erro Interno: Não foi possível realizar o processamento da requisição de feedback.'
      }
    };
  }
}

app.http('feedback', {
  methods: ['POST'],
  authLevel: 'function', // 4. Adicionado Authlevel
  handler: feedbackHandler
});
