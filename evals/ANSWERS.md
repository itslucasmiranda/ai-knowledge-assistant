# Avaliação das respostas

O conjunto `answers_pt_br_v1` contém quatro documentos sintéticos sobre o projeto fictício Atlas e 12 perguntas: oito respondíveis e quatro sem informação suficiente. Uma pergunta respondível exige duas fontes. Este é um conjunto de desenvolvimento pequeno, criado para este projeto; não constitui benchmark independente ou de produção.

## Executar

Na raiz do projeto, com as dependências instaladas e a chave Groq configurada:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_answers
```

O script usa os embeddings e o gerador reais. Cria e remove um banco SQLite temporário, sem ler ou alterar `data/documents.sqlite3`. O conjunto sintético é enviado ao provedor nas perguntas e nos trechos recuperados. A execução faz até 12 chamadas ao LLM e utiliza a cota da conta.

Os pesos de embeddings podem ser baixados na primeira execução. Há uma pausa de dez segundos entre perguntas para reduzir a frequência das requisições; isso não garante ausência de limites de uso. Ajuste com `--delay 20` se necessário. Erros não são repetidos automaticamente e permanecem no relatório e nos denominadores das métricas. A execução termina com código 1 quando há erros de infraestrutura ou casos com falha; uma métrica baixa, por si só, não muda o código de saída.

O relatório recebe um nome exclusivo em `evals/results/answers_<horário_UTC>.json`. Para escolher o nome:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_answers --output evals/results/answers_review.json
```

Arquivos existentes nunca são sobrescritos. Resultados novos não são adicionados automaticamente ao Git. Revise o conteúdo antes de versioná-los, especialmente se usar `--dataset` com dados próprios.

## Métricas automáticas

| Campo | Cálculo e interpretação |
|---|---|
| `status_accuracy` | Casos cujo status coincide com o esperado / todos os casos. Erros contam como incorretos. |
| `answerable_answer_rate` | Casos respondíveis com status `answered` / casos respondíveis. Não verifica a correção do texto. |
| `unanswerable_abstention_rate` | Casos sem resposta com `insufficient_context` / casos sem resposta. |
| `source_document_recall` | Média, nos casos respondíveis, da fração de documentos relevantes presentes nas fontes citadas. |
| `source_document_precision` | Média, nos casos respondíveis, da fração de documentos citados que são relevantes. Ausência de citações vale zero. |
| `error_count` | Casos em que a execução lançou uma exceção; o relatório registra somente o nome da classe do erro. |
| `latency_p50_ms`, `latency_p95_ms` | Percentis pelo método nearest-rank sobre a duração de cada tentativa, incluindo falhas. |

Grupos sem casos recebem `null`, nunca uma pontuação inventada. As métricas de fontes usam conjuntos de documentos, sem contar várias citações do mesmo documento como vários acertos. Elas não provam que cada afirmação da resposta está sustentada.

A latência mede recuperação e geração, excluindo a preparação inicial e as pausas. `setup_ms` mede criação do banco, segmentação e carregamento inicial do tokenizer/modelo. Não há aquecimento separado da inferência: a primeira pergunta pode ser mais lenta. O relatório não mede custos financeiros nem consumo de tokens do provedor.

## Revisão humana

Cada caso mantém pergunta, resposta de referência, resposta gerada e os trechos citados. Os campos `human_review` começam vazios e não participam das métricas automáticas. Preencha-os depois de ler a resposta e as fontes:

- `correct`: os fatos respondem corretamente à pergunta e estão de acordo com a referência?
- `supported_by_sources`: todas as afirmações factuais são sustentadas pelos trechos citados?
- `complete`: a resposta cobre o que foi perguntado, inclusive quando exige duas fontes?
- `notes`: explique erros, omissões ou a adequação de uma recusa.

Não use apenas coincidência de palavras ou a presença de `source_id` para declarar fidelidade. Preserve o relatório original antes de registrar uma revisão em outra cópia.

## Evidências e limites

A primeira execução real está preservada no [relatório JSON](results/answers_20261113T023133226390Z.json), com [análise dos 12 casos](ANSWERS_BASELINE.md). Foram 11/12 status corretos, 7/8 perguntas respondíveis respondidas, 4/4 recusas adequadas e zero erros de execução. O caso a05 recusou uma pergunta sobre PDF cuja resposta estava no conjunto. Os campos de revisão humana independente permanecem vazios; a análise assistida e suas limitações estão documentadas separadamente.

O relatório registra nomes dos modelos, hash do conjunto e do prompt, revisão Git quando disponível, indicação de alterações locais e versões das dependências. A revisão dos pesos e a versão servida pelo provedor não estão fixadas; os resultados podem variar. Depois de ajustes baseados neste conjunto, use um conjunto separado para avaliar generalização.

Os testes automatizados usam respostas controladas para verificar os cálculos, o isolamento do banco, a preservação das referências, o registro de erros e a proteção contra sobrescrita. Eles não medem a qualidade do modelo real.
