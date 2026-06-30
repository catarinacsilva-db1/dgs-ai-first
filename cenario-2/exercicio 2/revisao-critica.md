# Revisao critica do codigo gerado

## Escopo revisado
- src/shared/retry.ts
- src/functions/query/validator.ts
- tests/unit/retry.test.ts

## Achados (priorizados por severidade)

### 1) Medio - Politica de retry muito permissiva para uso em chamadas Azure
Referencia: src/shared/retry.ts (linhas 74-76 e 93-116)

Problema
- Quando shouldRetry nao eh informado, o utilitario repete para qualquer erro.
- Para integracoes Azure, isso pode causar retries em erros nao-transientes (por exemplo, erro de contrato de payload), aumentando latencia e custo sem chance real de recuperacao.

Risco
- Retentativas desnecessarias em falhas permanentes.
- Possivel efeito colateral quando a operacao nao eh idempotente.

Ajuste recomendado
- Definir uma politica padrao mais segura (retry apenas para erros transientes).
- Alternativamente, exigir shouldRetry para cenarios de producao e falhar cedo quando ausente.
- Documentar explicitamente no JSDoc que o default atual retenta qualquer erro.

### 2) Medio - Cobertura de teste insuficiente para o comportamento de backoff e callbacks
Referencia: tests/unit/retry.test.ts (linhas 6-41)

Problema
- Os testes atuais validam apenas:
  - sucesso na 3a tentativa
  - propagacao do erro ao exceder tentativas
- Nao ha validacao de:
  - progressao do atraso exponencial
  - chamada de onRetry por tentativa
  - comportamento de shouldRetry interrompendo retries

Risco
- Regressao silenciosa nos pontos mais criticos do utilitario (timing e observabilidade).

Ajuste recomendado
- Adicionar testes unitarios para:
  - ordem de delays (ex.: 100, 200, 400)
  - quantidade e payload das chamadas de onRetry
  - cenario com shouldRetry retornando false na primeira falha

### 3) Baixo - Validador retorna ZodError cru, sem contrato de erro de dominio
Referencia: src/functions/query/validator.ts (linhas 9-10)

Problema
- validateQueryRequest usa parse diretamente e propaga ZodError bruto.
- Isso tende a acoplar o chamador ao formato interno do Zod e dificulta padronizar resposta de erro 400 no endpoint.

Risco
- Inconsistencia de payload de erro quando integrar no handler.

Ajuste recomendado
- Usar safeParse e mapear para um objeto/erro de dominio padronizado (codigo, mensagem, detalhes).
- Manter o parse no limite da aplicacao (handler), nao espalhado na camada de dominio.

## Observacoes finais
- A base implementada eh boa para bootstrap e atende o objetivo inicial de stubs + primeiro ciclo funcional.
- Antes de um code review real de PR, os 3 ajustes acima reduzem risco tecnico e evitam discussao recorrente de qualidade no reviewer.
