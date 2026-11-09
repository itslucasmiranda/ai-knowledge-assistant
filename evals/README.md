# Avaliação de recuperação

Avaliação inicial da busca semântica com documentos sintéticos em português.

## Conjunto de dados

O arquivo `retrieval.json` contém:

- 6 documentos sintéticos.
- 12 perguntas.
- Uma fonte esperada por pergunta.
- Um trecho por documento.

Todas as consultas pesquisam no conjunto completo de documentos, sem filtro
pela fonte esperada. O gabarito é utilizado somente no cálculo das métricas.

A exigência de um trecho por documento permite interpretar as posições
retornadas como posições de documentos. A avaliação precisa ser adaptada
antes de incluir documentos com vários trechos.

## Executar

Na raiz do projeto, com as dependências instaladas:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_retrieval
```

Não é necessário iniciar a API.

O avaliador cria um banco SQLite temporário e utiliza o modelo real
`intfloat/multilingual-e5-small` em CPU. O banco da aplicação não é alterado.

O relatório é salvo em `evals/results/retrieval_baseline.json`.
Uma nova execução substitui esse arquivo.

## Métricas

- **Hit@1:** proporção de perguntas com uma fonte relevante em primeiro lugar.
- **Hit@3:** proporção de perguntas com uma fonte relevante entre os três primeiros resultados.
- **MRR@3:** média do inverso da posição da primeira fonte relevante, considerando somente os três primeiros resultados. Quando nenhuma fonte relevante aparece nesse intervalo, a contribuição é zero.

As métricas incluem todas as perguntas, inclusive os erros de recuperação.

## Resultado inicial

| Métrica | Resultado |
|---|---:|
| Hit@1 | 0,8333 |
| Hit@3 | 1,0000 |
| MRR@3 | 0,9028 |

A fonte esperada apareceu em primeiro lugar em 10 das 12 perguntas e
entre os três primeiros resultados em todas as perguntas.

### Casos fora da primeira posição

| Pergunta | Primeiro resultado | Fonte esperada | Posição da fonte esperada |
|---|---|---|---:|
| q05: Posso enviar um documento em PDF? | envio.txt | formatos.txt | 2 |
| q08: O upload retornou erro 413. O que isso significa? | consulta.txt | tamanho.txt | 3 |

Esses casos mostram erros de ordenação entre documentos do mesmo domínio.
Ainda não foi realizado um experimento controlado para determinar suas causas.

## Ambiente registrado

- Python: 3.14.7
- Sentence Transformers: 6.2.0
- Transformers: 5.22.1
- PyTorch: 2.15.0+cpu
- Modelo: intfloat/multilingual-e5-small
- Dispositivo: CPU

O relatório inclui as versões, o hash SHA-256 do arquivo de avaliação,
a data da execução, os resultados por pergunta e as métricas agregadas.

A revisão exata dos arquivos do modelo ainda não está fixada. Portanto,
o registro atual não garante resultados numericamente idênticos entre ambientes.

## Testes

Os testes em `tests/test_evaluation.py` verificam os cálculos das métricas,
incluindo posições, ausência de resultados relevantes e médias com erros.

Eles utilizam rankings construídos manualmente e não executam o modelo real.

## Limitações

Este conjunto é pequeno, sintético e específico ao domínio da aplicação.
O resultado não representa desempenho em documentos reais ou em produção.

Todas as perguntas possuem uma fonte relevante no conjunto. A avaliação
não mede a capacidade de reconhecer perguntas sem resposta.

Também não mede geração de respostas, fidelidade, latência ou custos.

Este conjunto passa a servir como referência de desenvolvimento.
Melhorias ajustadas com base nele deverão ser verificadas posteriormente
em um conjunto separado, que não tenha orientado os ajustes.