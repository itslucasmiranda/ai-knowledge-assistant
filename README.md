# AI Knowledge Assistant

> **Status: em desenvolvimento.** API para ingestão, segmentação e armazenamento de documentos, com busca semântica disponível como módulo Python. O endpoint HTTP de busca e a geração de respostas com RAG ainda estão em implementação.

## Objetivo

Construir uma API em Python para perguntas sobre documentos usando Retrieval-Augmented Generation (RAG), com recuperação de trechos relevantes, respostas fundamentadas em fontes e avaliação reproduzível.

## Funcionalidades implementadas

- API FastAPI com endpoint de verificação de saúde.
- Processamento de arquivos `.txt` em UTF-8, com ou sem BOM.
- Validação de extensão, conteúdo e tamanho máximo de 1 MiB.
- Segmentação em trechos de até 100 palavras, com sobreposição de 20 palavras.
- Identificação do documento pelo SHA-256 dos bytes enviados.
- Persistência de documentos e trechos em SQLite.
- Consulta de documentos pelo identificador.
- Preservação do registro original ao reenviar conteúdo idêntico.
- Leitura de trechos com metadados de origem e filtro por documento.
- Geração de embeddings com `intfloat/multilingual-e5-small`, executado em CPU.
- Validação de entradas vazias e do limite de tokens antes da geração de embeddings.
- Busca semântica nos trechos persistidos, com ordenação por similaridade.
- Retorno do texto, documento, arquivo de origem, posição do trecho e pontuação.
- Limitação da quantidade de resultados com `top_k`.
- Demonstração com modelo real e banco temporário.
- Testes automatizados e workflow no GitHub Actions.

## Tecnologias

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12 ou superior |
| API | FastAPI e Uvicorn |
| Validação de dados | Pydantic |
| Persistência | SQLite |
| Embeddings | Sentence Transformers e PyTorch |
| Modelo pré-treinado | intfloat/multilingual-e5-small |
| Recuperação | Similaridade de cosseno sobre embeddings normalizados |
| Testes | pytest |
| Integração contínua | GitHub Actions |

Docker, índice vetorial persistente e integração com um modelo de linguagem fazem parte das próximas etapas.

## Organização do código

| Arquivo | Responsabilidade |
|---|---|
| `app/main.py` | Endpoints, validação do upload e modelos de resposta |
| `app/chunking.py` | Segmentação de texto com sobreposição |
| `app/storage.py` | Persistência, consulta de documentos e leitura de trechos |
| `app/embeddings.py` | Geração de embeddings para perguntas e trechos |
| `app/retrieval.py` | Busca semântica com pontuação e metadados de origem |
| `scripts/demo_search.py` | Demonstração com modelo real e banco temporário |
| `tests/` | Testes automatizados e isolamento do banco |
| `.github/workflows/tests.yml` | Execução dos testes no GitHub Actions |

O fluxo atual da API recebe o documento, valida o conteúdo, gera os trechos e persiste os dados no SQLite.

O módulo de recuperação lê os trechos armazenados, gera embeddings e ordena os resultados por similaridade com a pergunta. A busca ainda não possui endpoint HTTP.

## Roadmap

- [x] API inicial com `GET /health`
- [x] Ingestão de documentos e segmentação de texto
- [x] Persistência em SQLite e consulta por identificador
- [x] Módulo de embeddings local com validação de entradas
- [x] Integração dos embeddings com a leitura dos trechos persistidos
- [x] Busca semântica local com pontuação e metadados de origem
- [x] Demonstração da busca com modelo real
- [x] Testes automatizados e workflow no GitHub Actions
- [ ] Endpoint HTTP de busca semântica
- [ ] Índice vetorial persistente
- [ ] Endpoint de perguntas com respostas e fontes
- [ ] Avaliação reproduzível da recuperação e das respostas
- [ ] Observabilidade de latência, erros e custos
- [ ] Docker e demonstração da aplicação completa

## Requisitos

- Python 3.12 ou superior.
- Terminal PowerShell para os comandos abaixo.
- Conexão com a internet para instalar as dependências e baixar o modelo na primeira execução.

O armazenamento utiliza a opção `autocommit` do módulo SQLite, disponível a partir do Python 3.12.

## Executar localmente no Windows

Execute os comandos na pasta do projeto, onde estão `requirements.txt`, `app` e `tests`.

Crie o ambiente virtual:

```powershell
py -m venv .venv
```

Instale o PyTorch para CPU:

```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Instale as dependências do projeto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Inicie a API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Acesse:

- Documentação interativa: http://127.0.0.1:8000/docs
- Verificação de saúde: http://127.0.0.1:8000/health

Mantenha o terminal aberto enquanto utiliza a API. Para encerrar o servidor, pressione `Ctrl + C`.

Os comandos usam diretamente o Python do ambiente virtual, sem exigir sua ativação no PowerShell.

## Endpoints disponíveis

| Método | Rota | Função |
|---|---|---|
| GET | `/health` | Retorna `{"status": "ok"}` |
| POST | `/documents` | Recebe, segmenta e persiste um documento |
| GET | `/documents/{document_id}` | Consulta um documento persistido |

### Enviar um documento

1. Abra a documentação em `/docs`.
2. Expanda `POST /documents`.
3. Clique em `Try it out`.
4. Selecione um arquivo `.txt` no campo `file`.
5. Clique em `Execute`.

O envio utiliza `multipart/form-data`.

A resposta contém:

| Campo | Conteúdo |
|---|---|
| `document_id` | SHA-256 dos bytes do arquivo |
| `filename` | Nome do arquivo |
| `chunk_count` | Quantidade de trechos |
| `chunks` | Lista de trechos com `index` e `text` |

Ao reenviar os mesmos bytes, a API reutiliza o documento existente e preserva seu nome original.

### Consultar um documento

1. Copie o valor de `document_id` retornado pelo upload, sem as aspas.
2. Expanda `GET /documents/{document_id}`.
3. Clique em `Try it out`.
4. Cole o identificador no campo `document_id`.
5. Clique em `Execute`.

A consulta retorna o documento e seus trechos. Se o identificador não existir, retorna HTTP 404.

### Códigos de resposta

| Código | Significado |
|---|---|
| 200 | Operação concluída |
| 400 | Conteúdo vazio, UTF-8 inválido ou presença de caractere nulo |
| 404 | Documento não encontrado |
| 413 | Arquivo maior que 1 MiB, equivalente a 1.048.576 bytes |
| 415 | Extensão diferente de `.txt` |
| 422 | Campo obrigatório ausente ou requisição incompatível |

## Persistência

Os documentos e seus trechos ficam em `data/documents.sqlite3`. O diretório e as tabelas são criados automaticamente quando o armazenamento é inicializado.

Os registros permanecem disponíveis após reiniciar a API, desde que o arquivo do banco seja preservado.

Os arquivos locais do SQLite são excluídos do versionamento pelo `.gitignore`. Os testes utilizam bancos temporários, isolados dos dados da aplicação.

## Embeddings

O módulo `app/embeddings.py` utiliza o modelo pré-treinado
[intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small).

- `embed_query` representa perguntas com o prefixo `query:`.
- `embed_passages` representa trechos com o prefixo `passage:`.
- Os vetores são normalizados e possuem 384 dimensões.
- Entradas vazias são rejeitadas.
- O limite de tokens é verificado incluindo o prefixo e os tokens especiais.
- Entradas acima do limite são rejeitadas para evitar truncamento silencioso.
- O modelo é carregado sob demanda e mantido em cache no processo.
- A execução utiliza CPU.

O modelo é pré-treinado por terceiros. Este projeto implementa sua integração, sem treinamento ou ajuste fino próprio.

### Verificação com o modelo real

Na pasta do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -c "from app.embeddings import embed_query, embed_passages; query = embed_query('Onde ficam salvos os documentos?'); passages = embed_passages(['Os documentos ficam armazenados no SQLite.']); print('Dimensoes da pergunta:', len(query)); print('Quantidade de trechos:', len(passages)); print('Dimensoes do trecho:', len(passages[0]))"
```

Resultado esperado:

```text
Dimensoes da pergunta: 384
Quantidade de trechos: 1
Dimensoes do trecho: 384
```

A primeira execução baixa os arquivos do modelo. Essa verificação confirma o carregamento e as dimensões dos vetores; ela não substitui uma avaliação da qualidade da busca.

## Busca semântica

A função `search_documents`, em `app/retrieval.py`, realiza a recuperação dos trechos:

1. Valida a pergunta e o parâmetro `top_k`.
2. Lê os trechos do SQLite, com filtro opcional por documento.
3. Gera os embeddings da pergunta e dos trechos.
4. Calcula a similaridade usando o produto escalar dos vetores normalizados, equivalente à similaridade de cosseno.
5. Ordena os resultados por pontuação e retorna até `top_k` trechos.

Em caso de empate, os resultados são ordenados pelo identificador do documento e pela posição do trecho.

### Parâmetros

| Parâmetro | Descrição |
|---|---|
| `store` | Instância de `DocumentStore` |
| `query` | Pergunta ou texto de consulta; não pode estar vazio |
| `top_k` | Quantidade máxima de resultados, entre 1 e 20; padrão: 3 |
| `document_id` | Filtro opcional para pesquisar em um único documento |

Se não houver trechos correspondentes ao filtro, a função retorna uma lista vazia.

### Resultado

Cada resultado contém:

| Campo | Conteúdo |
|---|---|
| `document_id` | Identificador do documento de origem |
| `filename` | Nome do arquivo de origem |
| `chunk_index` | Posição do trecho, começando em zero |
| `text` | Conteúdo do trecho |
| `score` | Similaridade com a consulta |

A recuperação devolve trechos existentes. Ela ainda não gera uma resposta em linguagem natural.

## Demonstração da busca semântica

Execute na pasta do projeto:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo_search
```

Não é necessário iniciar a API para executar essa demonstração.

O script cria três documentos sintéticos em um banco SQLite temporário, executa duas consultas com o modelo real e exibe os resultados ordenados. Os documentos da aplicação não são alterados.

| Pergunta | Primeiro resultado esperado |
|---|---|
| Onde ficam salvos os documentos? | `armazenamento.txt` |
| Como recuperar o acesso se eu esquecer minha senha? | `acesso.txt` |

Na verificação manual inicial, os dois documentos esperados apareceram em primeiro lugar.

Essa demonstração verifica a integração entre armazenamento, embeddings e recuperação. Não substitui uma avaliação com um conjunto maior de perguntas e documentos. As pontuações podem variar entre ambientes e versões.

## Executar os testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

A suíte cobre:

- Resposta do endpoint de saúde.
- Validações do upload e limites de tamanho.
- Segmentação e sobreposição de trechos.
- Persistência, duplicidade e consulta de documentos.
- Leitura de trechos com ordenação e metadados de origem.
- Filtro por documento e tratamento de identificadores como parâmetros SQL.
- Isolamento do armazenamento durante os testes.
- Entradas vazias, prefixos e limites de tokens dos embeddings.
- Ordenação dos resultados da busca e preservação das fontes.
- Limite de resultados com `top_k`.
- Banco vazio e propagação de erros da geração de embeddings.

Os testes de embeddings e recuperação utilizam modelos ou funções de codificação simulados. Após instalar as dependências, a suíte não precisa baixar os pesos do modelo nem executar inferência real.

A demonstração em `scripts/demo_search.py` exercita separadamente o modelo real.

O workflow do GitHub Actions executa os testes em pushes e pull requests.

## Limitações atuais

A busca semântica está disponível como módulo Python, sem endpoint HTTP. Ainda não há geração de respostas com LLM.

Os embeddings dos trechos são recalculados a cada consulta. O modelo permanece em cache no processo, mas os vetores dos documentos ainda não são persistidos. A implementação lê e compara todos os trechos selecionados, sendo destinada inicialmente a pequenos conjuntos de documentos.

A busca retorna os primeiros resultados por similaridade, sem um limiar mínimo de relevância. Portanto, pode retornar trechos sem relação suficiente com a pergunta. Pontuações de similaridade não representam probabilidades de uma resposta estar correta.

A segmentação considera palavras, não tokens, e normaliza espaços e quebras de linha. Um trecho de 100 palavras ainda pode ultrapassar o limite de tokens do modelo. Nesse caso, o módulo de embeddings rejeita a entrada e a busca propaga o erro. O tratamento desse caso na ingestão ainda está pendente.

O limite de 1 MiB é verificado no endpoint após o processamento multipart. Controles de recebimento para implantação pública ainda não foram implementados.

A qualidade da recuperação semântica ainda precisa ser avaliada com um conjunto reproduzível e mais abrangente de documentos e perguntas.

O projeto está preparado para desenvolvimento local. Autenticação e controles de implantação pública ainda não foram implementados.

## Princípios

- Utilizar documentos públicos ou sintéticos nos exemplos e avaliações.
- Não versionar documentos confidenciais, bancos locais ou chaves de API.
- Diferenciar funcionalidades implementadas de objetivos planejados.
- Registrar decisões técnicas, resultados e limitações.
- Desenvolver por branches, commits descritivos e pull requests.

## Autor

[Lucas Miranda](https://github.com/itslucasmiranda)