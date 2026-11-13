# Análise da execução de respostas da v1

Relatório: [answers_20261113T023133226390Z.json](results/answers_20261113T023133226390Z.json).

Execução realizada pelo mantenedor em 12/11/2026 às 23h31–23h34 (America/Bahia), registrada no relatório em 13/11/2026 UTC. Geração com `openai/gpt-oss-20b` na Groq e embeddings locais `intfloat/multilingual-e5-small`. Os resultados abaixo pertencem a uma única execução de um conjunto sintético de desenvolvimento.

## Resultados

| Medida | Resultado |
|---|---:|
| Casos executados | 12 |
| Erros de execução | 0 |
| Concordância com o status esperado | 11/12 (91,67%) |
| Perguntas respondíveis respondidas | 7/8 (87,5%) |
| Perguntas sem informação corretamente recusadas | 4/4 (100%) |
| Recall médio dos documentos citados | 87,5% |
| Precisão média dos documentos citados | 87,5% |
| Latência p50 (nearest-rank) | 568,65 ms |
| Latência p95 (nearest-rank) | 1.033,48 ms |
| Preparação inicial | 75.077,79 ms |

A preparação e as pausas de dez segundos entre perguntas não estão incluídas nos percentis. Com apenas 12 observações, o p95 corresponde ao maior tempo observado; não representa uma distribuição de desempenho de produção. A precisão/recall das fontes atribui zero ao caso respondível recusado. Não são métricas de veracidade de cada afirmação.

## Conferência das respostas e fontes

Esta é uma análise assistida do relatório, comparada com o conjunto de referência. Não substitui uma avaliação humana independente. O JSON original foi preservado, inclusive com os campos `human_review` vazios.

| Caso | Resultado observado | Conferência do conteúdo |
|---|---|---|
| a01 | Respondido | Banco SQLite e caminho do arquivo correspondem à fonte `armazenamento.txt`. |
| a02 | Respondido | Preservação após reinício e condição de manter o arquivo estão explícitas na fonte. |
| a03 | Respondido | E-mail, dias, horário e ausência de atendimento nos fins de semana correspondem a `suporte.txt`. |
| a04 | Respondido | Prazo de até dois dias úteis corresponde a `suporte.txt`. |
| a05 | Recusa indevida | A pergunta sobre PDF tem resposta explícita em `envio.txt`: PDF e DOCX não são aceitos. |
| a06 | Respondido | Limite de 1 MiB e equivalência de 1.048.576 bytes correspondem a `envio.txt`. |
| a07 | Respondido | `POST /ask` e filtro `document_id` correspondem a `busca.txt`. |
| a08 | Respondido | Local de armazenamento e e-mail são sustentados pelas duas fontes citadas. |
| a09 | Recusa adequada | O conjunto não informa preço de plano profissional. |
| a10 | Recusa adequada | O conjunto informa e-mail de suporte, mas não telefone. |
| a11 | Recusa adequada | O conjunto não identifica provedor de hospedagem. |
| a12 | Recusa adequada | O conjunto não informa data de lançamento. |

Nas sete respostas com status `answered`, não foram identificadas afirmações sem apoio nos trechos citados nesta análise. Isso não permite declarar fidelidade geral de 100%, ausência de alucinações ou qualidade comprovada fora destes exemplos.

## Limitação identificada: a05

Pergunta: **Posso enviar um PDF de 500 KB?**

Resposta esperada: **Não. Só arquivos .txt em UTF-8 são aceitos.**

Resposta observada: `insufficient_context`, sem fontes citadas.

O resultado é uma recusa indevida em uma pergunta respondível, e não uma exceção de infraestrutura. A restrição de formato já basta para responder; o tamanho de 500 KB não torna PDF um formato aceito.

O relatório conserva apenas as fontes citadas na resposta final. Quando há recusa, essa lista fica vazia e não revela quais trechos foram recuperados e enviados ao gerador. Portanto, o relatório isolado não comprova a causa da recusa. No código de referência, quatro documentos curtos, `top_k=5` e ausência de filtro tornam plausível que todos tenham sido incluídos; isso é uma inferência, não um registro da chamada.

O resultado permanece como referência da v1. Não houve alteração do prompt, do conjunto ou seleção de uma execução posterior para ocultar a falha. Uma investigação futura pode registrar o contexto recuperado em avaliações com dados sintéticos e avaliar perguntas sobre restrições em um conjunto separado.

## Proveniência e verificações

- Revisão declarada na execução: `1960cc256d5666ac256594051a9cc42334077b97`.
- `working_tree_dirty: true`: havia alterações ou arquivos não rastreados no ambiente. O relatório não informa quais; a execução não pode ser certificada como reprodução de um checkout limpo.
- As 12 definições de casos correspondem ao conjunto versionado. Os textos, nomes e identificadores das fontes citadas também correspondem aos documentos desse conjunto.
- As métricas foram recalculadas a partir dos casos e coincidem com os valores registrados.
- O hash do prompt coincide com o prompt versionado. O hash dos bytes do conjunto coincide com o arquivo usando finais de linha CRLF do Windows; a cópia LF tem hash diferente, mas o conteúdo JSON coincide.
- Python, sistema operacional e versões das bibliotecas estão no relatório original. Os pesos e a versão servida pelo provedor não estão fixados.
- SHA-256 do relatório original: `e5b0a5ff0e8489570d9924db682c249df0586b83eef21f29935d8aa2d1e31fcb`.

O relatório contém apenas o corpus sintético e os metadados da execução, sem chave de API. Sua preservação não equivale a uma nova execução dos modelos pelo revisor.
