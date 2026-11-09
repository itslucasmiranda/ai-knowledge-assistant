# AI Knowledge Assistant

> **Status: em desenvolvimento.** API para ingestão, armazenamento e busca semântica em documentos. A recuperação de trechos está implementada. Há uma avaliação inicial da recuperação com dados sintéticos. A geração de respostas com um modelo de linguagem e a avaliação dessas respostas são próximas etapas.

## Objetivo

Construir uma aplicação de perguntas sobre documentos usando Retrieval-Augmented Generation (RAG), com recuperação de contexto, respostas fundamentadas em fontes e avaliação reproduzível.

A implementação atual cobre ingestão, persistência e recuperação semântica. O endpoint de busca retorna trechos dos documentos e seus metadados de origem.

## Funcionalidades implementadas

- API FastAPI com documentação interativa.
- Verificação de saúde com `GET /health`.
- Upload de arquivos `.txt` em UTF-8, com ou sem BOM.
- Validação de extensão, conteúdo e tamanho máximo de 1 MiB.
- Segmentação inicial em trechos de até 100 palavras, com sobreposição de 20.
- Divisão adicional dos trechos que excedem o limite de tokens, antes da persistência.
- Tratamento de trechos antigos acima do limite durante a busca, sem alterar o banco.
- Identificação de documentos pelo SHA-256 dos bytes enviados.
- Persistência de documentos e trechos em SQLite.
- Consulta de documentos pelo identificador.
- Preservação do registro original ao reenviar conteúdo idêntico.
- Embeddings locais com `intfloat/multilingual-e5-small`, executado em CPU.
- Validação de entradas vazias e do limite de tokens dos embeddings.
- Busca semântica via `POST /search`.
- Filtro opcional por documento e limite de resultados com `top_k`.
- Resultados com texto, pontuação e metadados da fonte.
- Demonstração com modelo real e banco temporário.
- Testes automatizados e workflow no GitHub Actions.

## Tecnologias

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12 ou superior |
| API | FastAPI e Uvicorn |
| Validação | Pydantic |
| Persistência | SQLite |
| Embeddings | Sentence Transformers e PyTorch |
| Modelo pré-treinado | intfloat/multilingual-e5-small |
| Recuperação | Similaridade de cosseno sobre vetores normalizados |
| Testes | pytest |
| Integração contínua | GitHub Actions |

## Organização do código

| Arquivo ou diretório | Responsabilidade |
|---|---|
| `app/main.py` | Endpoints, validação das requisições e respostas |
| `app/chunking.py` | Segmentação inicial por palavras com sobreposição |
| `app/token_chunking.py` | Divisão de texto conforme uma função de contagem de tokens |
| `app/storage.py` | Persistência, consulta e leitura de trechos |
| `app/embeddings.py` | Geração de embeddings, validação e divisão com o tokenizer do modelo |
| `app/retrieval.py` | Recuperação, pontuação e ordenação dos trechos |
| `scripts/demo_search.py` | Demonstração com modelo real |
| `scripts/validate_token_chunking.py` | Validação de upload e busca com textos acima do limite e modelo real |
| `scripts/evaluate_retrieval.py` | Avaliação inicial da recuperação |
| `evals/` | Conjunto sintético, metodologia e relatório de referência |
| `tests/` | Testes automatizados com armazenamento isolado |
| `.github/workflows/tests.yml` | Execução dos testes no GitHub Actions |

## Fluxo da aplicação

Na ingestão, a API valida o arquivo e calcula seu identificador. Se ele já existir, retorna o documento preservado. Para novos documentos, segmenta o texto por palavras, subdivide os trechos que excedem o limite de tokens e persiste o resultado no SQLite.

Na busca, a API valida a consulta, lê os trechos selecionados e subdivide em memória os que excedem o limite de tokens. Depois, gera embeddings e calcula a similaridade com a pergunta. Cada trecho armazenado contribui com no máximo um resultado, representado pela parte de maior pontuação e pelos metadados do trecho original.

O modelo é reutilizado dentro do processo. O primeiro upload de um documento novo também pode carregar e baixar o modelo, pois usa seu tokenizer. Os embeddings dos documentos ainda são recalculados a cada busca.

## Roadmap

- [x] API inicial com endpoint de saúde
- [x] Ingestão e segmentação de documentos
- [x] Persistência em SQLite e consulta por identificador
- [x] Embeddings locais com validação de entradas
- [x] Segmentação conforme o limite de tokens e compatibilidade com documentos antigos
- [x] Recuperação semântica com pontuação e fontes
- [x] Endpoint HTTP de busca semântica
- [x] Demonstração com modelo real
- [x] Testes automatizados e workflow no GitHub Actions
- [x] Avaliação inicial da recuperação com conjunto sintético
- [ ] Ampliar a avaliação com conjunto independente e perguntas sem resposta
- [ ] Persistência de embeddings e indexação vetorial
- [ ] Endpoint de perguntas com respostas geradas e fontes
- [ ] Avaliação de fidelidade das respostas
- [ ] Observabilidade de latência, erros e custos
- [ ] Docker e demonstração da aplicação completa

## Requisitos

- Python 3.12 ou superior.
- Git para obter o repositório.
- PowerShell para executar os comandos abaixo.
- Acesso à internet para instalar dependências e baixar o modelo na primeira execução.

O armazenamento utiliza o parâmetro `autocommit` do módulo SQLite, disponível a partir do Python 3.12.

## Executar localmente no Windows

Execute os comandos na pasta do projeto, onde estão `requirements.txt`, `app` e `tests`.

### Preparar o ambiente

Crie o ambiente virtual:

```powershell
py -m venv .venv
```

Instale o PyTorch para CPU:

```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Instale as dependências:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Os comandos utilizam diretamente o Python do ambiente virtual, sem exigir sua ativação no PowerShell.

### Iniciar a API

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Acesse:

- [Documentação interativa](http://127.0.0.1:8000/docs)
- [Verificação de saúde](http://127.0.0.1:8000/health)

Mantenha o terminal aberto enquanto utiliza a API. Para encerrar, pressione `Ctrl + C`.

Após reiniciar o computador, execute novamente o comando do Uvicorn na pasta do projeto. Não é necessário reinstalar as dependências se o ambiente virtual estiver preservado.

## Endpoints

| Método | Rota | Função |
|---|---|---|
| GET | `/health` | Retorna `{"status": "ok"}` |
| POST | `/documents` | Recebe, segmenta e persiste um documento |
| GET | `/documents/{document_id}` | Consulta um documento persistido |
| POST | `/search` | Recupera trechos por similaridade com uma consulta |

## Enviar e consultar documentos

### Upload

1. Abra `/docs`.
2. Expanda `POST /documents`.
3. Clique em `Try it out`.
4. Selecione um arquivo `.txt` no campo `file`.
5. Clique em `Execute`.
6. Confira o código em `Server response` e o conteúdo de `Response body`.

Selecionar o arquivo não realiza o envio. O upload ocorre após clicar em `Execute`.

A requisição utiliza `multipart/form-data`.

| Campo da resposta | Conteúdo |
|---|---|
| `document_id` | SHA-256 dos bytes enviados |
| `filename` | Nome do arquivo armazenado |
| `chunk_count` | Quantidade de trechos |
| `chunks` | Trechos com `index` e `text` |

Ao reenviar os mesmos bytes, a API reutiliza o documento existente e preserva seu nome original.

### Consulta por identificador

1. Copie o `document_id` retornado pelo upload.
2. Abra `GET /documents/{document_id}`.
3. Clique em `Try it out`.
4. Cole o identificador no campo, sem aspas.
5. Clique em `Execute`.

A API retorna HTTP 200 com o documento e seus trechos. Se o identificador não existir, retorna HTTP 404.

## Busca semântica pela API

O endpoint `POST /search` recebe JSON.

### Parâmetros

| Campo | Obrigatório | Regra |
|---|---|---|
| `query` | Sim | Texto não vazio, com até 2.000 caracteres após remover espaços das extremidades |
| `top_k` | Não | Inteiro entre 1 e 20; padrão: 3 |
| `document_id` | Não | Identificador com 64 caracteres hexadecimais minúsculos; restringe a busca a um documento |

Campos adicionais são rejeitados. `top_k` não aceita strings, valores booleanos ou números decimais.

O limite de caracteres da consulta não substitui a validação de tokens realizada antes da geração dos embeddings.

### Buscar nos documentos armazenados

Em `POST /search`, clique em `Try it out` e envie:

```json
{
  "query": "Onde ficam salvos os documentos?",
  "top_k": 3
}
```

Sem `document_id`, a busca considera todos os trechos armazenados.

### Buscar em um documento específico

Primeiro, envie um arquivo por `POST /documents`. Depois, use o identificador retornado:

```json
{
  "query": "Onde ficam salvos os documentos?",
  "top_k": 3,
  "document_id": "SUBSTITUA_PELO_DOCUMENT_ID_DO_UPLOAD"
}
```

O valor acima é um marcador. Substitua-o pelo identificador real, mantendo as aspas.

### Resposta

| Campo | Conteúdo |
|---|---|
| `query` | Consulta após remover espaços das extremidades |
| `result_count` | Quantidade de resultados retornados |
| `results` | Lista de trechos ordenados por similaridade |

Cada item de `results` contém:

| Campo | Conteúdo |
|---|---|
| `document_id` | Identificador do documento de origem |
| `filename` | Nome do arquivo de origem |
| `chunk_index` | Posição do trecho armazenado de origem, começando em zero |
| `text` | Texto recuperado; pode ser uma parte do trecho original quando ele exceder o limite |
| `score` | Similaridade entre o trecho e a consulta |

`top_k` define o máximo de resultados. Uma busca com `top_k: 3` pode retornar apenas um trecho se houver somente um disponível.

Quando um trecho armazenado precisa ser subdividido, somente sua parte de maior pontuação entra no ranking. `top_k` limita os resultados por trecho armazenado, não por documento: vários trechos do mesmo documento ainda podem aparecer.

O score não representa uma porcentagem de acerto nem a probabilidade de uma resposta estar correta.

### Busca sem resultados

Se o banco estiver vazio ou o filtro não encontrar trechos, a API retorna HTTP 200:

```json
{
  "query": "Onde ficam salvos os documentos?",
  "result_count": 0,
  "results": []
}
```

Um identificador válido, mas inexistente, produz uma busca vazia. Já a consulta desse identificador em `GET /documents/{document_id}` retorna HTTP 404.

Se um documento recém-enviado não aparecer, confirme o upload e copie o identificador de `Response body`. Os blocos `Example Value` do Swagger são exemplos da documentação, não resultados de requisições.

## Códigos de resposta

| Código | Situação |
|---|---|
| 200 | Operação concluída, incluindo busca sem resultados |
| 400 | Upload com conteúdo vazio, UTF-8 inválido ou caractere nulo |
| 404 | Documento inexistente na consulta por identificador |
| 413 | Upload maior que 1 MiB, equivalente a 1.048.576 bytes |
| 415 | Extensão diferente de `.txt` |
| 422 | Requisição inválida ou entrada rejeitada pela validação dos embeddings |
| 500 | Falha interna não tratada como erro de entrada |

No endpoint de busca, `EmbeddingInputError` é convertido em HTTP 422. Outras falhas internas não são classificadas como erros de validação da requisição.

## Persistência

Os documentos e trechos ficam em `data/documents.sqlite3`. O diretório e as tabelas são criados automaticamente quando o armazenamento é inicializado.

Os registros permanecem disponíveis após reiniciar a API, desde que o arquivo do banco seja preservado.

O `.gitignore` exclui os arquivos locais do SQLite do versionamento. A suíte de testes utiliza bancos temporários, isolados dos dados da aplicação.

## Embeddings e recuperação

O projeto integra o modelo pré-treinado
[intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small).

- Perguntas recebem o prefixo `query:`.
- Trechos recebem o prefixo `passage:`.
- Os vetores são normalizados e possuem 384 dimensões.
- A execução utiliza CPU.
- O modelo é carregado sob demanda e reutilizado no processo.
- A primeira execução precisa baixar os arquivos do modelo.
- Entradas vazias são rejeitadas.
- Perguntas acima do limite de tokens são rejeitadas.
- Os trechos são subdivididos antes da codificação; as funções de geração de embeddings mantêm a validação que rejeita entradas acima do limite.
- A contagem considera o prefixo e os tokens especiais.

O modelo é pré-treinado por terceiros. O projeto implementa sua integração, sem treinamento ou ajuste fino próprio.

A função `search_documents`, em `app/retrieval.py`:

1. Valida a consulta e `top_k`.
2. Lê os trechos persistidos, aplicando o filtro opcional por documento.
3. Gera o embedding da consulta e subdivide os trechos que excedem o limite.
4. Gera embeddings das partes e calcula o produto escalar dos vetores normalizados, equivalente à similaridade de cosseno.
5. Seleciona a parte de maior pontuação de cada trecho armazenado.
6. Ordena os resultados e retorna até `top_k` trechos.

Entre partes do mesmo trecho, um empate preserva a primeira parte. Entre resultados, empates são resolvidos pelo identificador do documento e pela posição do trecho.

A recuperação devolve conteúdo existente nos documentos. A geração de uma resposta com LLM ainda não está implementada.

## Demonstração com modelo real

Execute na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo_search
```

Não é necessário iniciar a API para essa demonstração.

O script cria três documentos sintéticos em um banco temporário, executa duas consultas e imprime os resultados ordenados. Ele não altera o banco da aplicação.

| Pergunta | Primeiro resultado esperado |
|---|---|
| Onde ficam salvos os documentos? | `armazenamento.txt` |
| Como recuperar o acesso se eu esquecer minha senha? | `acesso.txt` |

Na verificação manual inicial, os dois documentos esperados apareceram em primeiro lugar.

O endpoint HTTP também foi exercitado com um documento sobre armazenamento em SQLite. A consulta retornou HTTP 200, um trecho, metadados da fonte e score aproximado de 0,8643.

Essas verificações demonstram a integração com o modelo real. O teste HTTP com um único documento não mede a qualidade do ranking entre documentos concorrentes. As pontuações podem variar entre ambientes e versões.

## Segmentação por tokens

A segmentação inicial utiliza até 100 palavras e sobreposição de 20 palavras. Cada trecho passa depois pelo tokenizer de `multilingual-e5-small`, incluindo o prefixo `passage: ` e os tokens especiais.

O limite efetivo é o menor valor entre 512 e `model.max_seq_length`. Quando um trecho excede esse limite, ele é dividido próximo ao meio, preferindo espaços. Uma palavra muito longa pode ser dividida entre caracteres. O procedimento continua até que cada parte respeite o limite.

A divisão adicional não cria nova sobreposição. Portanto, as partes finais não têm garantia de sobreposição de 20 palavras entre todos os pares consecutivos. A segmentação também normaliza espaços e quebras de linha.

Novos uploads persistem os trechos já ajustados. Documentos antigos são subdivididos somente em memória durante a busca. Seus registros e índices permanecem intactos. Reenviar um documento idêntico retorna o registro existente, sem migrar seus trechos.

### Validar com o modelo real

Execute na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_token_chunking
```

O script usa o cliente de testes da API e um banco temporário. Não é necessário iniciar o Uvicorn. Ele verifica upload, persistência, busca em documentos novos e antigos e preservação do documento antigo.

Na execução local de 9 de novembro de 2026:

| Verificação | Resultado |
|---|---|
| Tokens do texto original, incluindo prefixo e tokens especiais | 1.814 |
| Limite efetivo do modelo | 512 |
| Trechos gerados no upload | 5 |
| Maior trecho, incluindo prefixo e tokens especiais | 453 |
| Upload, persistência e busca com modelo real | Aprovados |
| Preservação do documento antigo | Aprovada |

O tokenizer pode emitir um aviso ao contar o texto original acima do limite. Essa contagem é intencional; o texto completo não é enviado para a inferência de embeddings. A codificação recebe as partes que respeitam o limite.

Essa execução verifica a integração, não a qualidade do ranking. O modelo não tem uma revisão fixa configurada, portanto contagens e resultados não são garantidos como idênticos em outros ambientes.

## Testes automatizados

Execute:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

A execução local registrada nesta etapa apresentou **99 testes aprovados**, além de 4 subtestes.

A suíte verifica:

- Endpoint de saúde.
- Upload e validações de conteúdo, extensão e tamanho.
- Segmentação inicial e sobreposição.
- Divisão por tokens, preservação da ordem e tratamento de palavras longas.
- Persistência de trechos ajustados e reenvio sem novo carregamento do modelo.
- Busca em documentos antigos, seleção da melhor parte e preservação do banco.
- Persistência, duplicidade e consulta por identificador.
- Leitura de trechos com metadados e filtro por documento.
- Isolamento do armazenamento.
- Prefixos, entradas vazias e limites de tokens dos embeddings.
- Ordenação da recuperação e limite de resultados.
- Busca em banco vazio e filtro sem correspondência.
- Contrato HTTP do `/search`.
- Rejeição de parâmetros inválidos e campos extras.
- Conversão de erros esperados de embeddings em HTTP 422.
- Preservação de HTTP 500 para falhas internas, sem expor a mensagem interna na resposta testada.

Os testes de embeddings, recuperação e busca HTTP utilizam modelos ou funções de codificação simulados. Após instalar as dependências, a suíte não precisa baixar os pesos do modelo nem executar inferência real.

A demonstração, o teste manual pela API e o script de validação de tokens exercitam separadamente o modelo real.

O GitHub Actions executa a suíte em pushes e pull requests.

## Avaliação inicial da recuperação

A avaliação de referência anterior à correção de segmentação por tokens, com 6 documentos sintéticos e 12 perguntas, apresentou
Hit@1 de 83,33%, Hit@3 de 100% e MRR@3 de 0,9028.

Esses resultados descrevem somente esse conjunto inicial.
A metodologia, os erros de ordenação e as limitações estão em
[evals/README.md](evals/README.md).

## Limitações atuais

- Ainda não há geração de respostas com LLM.
- Os embeddings dos documentos são recalculados a cada consulta.
- Ainda não há persistência dos vetores nem índice vetorial.
- Todos os trechos selecionados são lidos e comparados. A implementação inicial é destinada a pequenos conjuntos de documentos.
- Não há limiar mínimo de relevância. A busca pode retornar trechos pouco relacionados à pergunta.
- A segmentação normaliza espaços e quebras de linha. A subdivisão por tokens não acrescenta sobreposição e pode separar palavras muito longas.
- A busca de documentos antigos usa a maior pontuação entre as partes de cada trecho. O efeito dessa política sobre a qualidade do ranking ainda precisa ser avaliado.
- A ingestão de documentos novos depende do carregamento do modelo e da tokenização, o que acrescenta latência.
- Não há orçamento global de quantidade de trechos ou de trabalho por requisição. O limite de arquivo não garante tempo de processamento baixo.
- A revisão dos arquivos do modelo ainda não está fixada.
- O limite de 1 MiB é verificado no endpoint após o processamento multipart.
- Autenticação, limites de requisições e controles para implantação pública ainda não foram implementados.
- A avaliação inicial utiliza um conjunto sintético pequeno. Ainda é necessário ampliar os dados e avaliar em um conjunto independente, incluindo perguntas sem resposta.

## Princípios

- Utilizar documentos públicos ou sintéticos nos exemplos e avaliações.
- Não versionar documentos confidenciais, bancos locais ou chaves de API.
- Diferenciar funcionalidades implementadas de objetivos planejados.
- Documentar decisões técnicas, evidências e limitações.
- Desenvolver por branches, commits descritivos e pull requests.
- Validar alterações com testes antes da integração.

## Autor

[Lucas Miranda](https://github.com/itslucasmiranda)
