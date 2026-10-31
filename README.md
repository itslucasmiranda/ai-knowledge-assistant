# AI Knowledge Assistant

> **Status: em desenvolvimento.** Projeto de portfólio de engenharia de IA. As funcionalidades abaixo são objetivos de implementação e não estão todas disponíveis.

## Objetivo
Construir uma API em Python para perguntas sobre documentos usando Retrieval-Augmented Generation (RAG), com recuperação de trechos, respostas fundamentadas em fontes e avaliação reproduzível.

## Arquitetura planejada
1. API HTTP com FastAPI e validação de dados.
2. Ingestão e segmentação de documentos públicos ou sintéticos.
3. Geração de embeddings e indexação vetorial.
4. Recuperação de contexto e integração com um modelo de linguagem.
5. Avaliação de recuperação, fidelidade das respostas, latência e custos.
6. Testes automatizados e integração contínua.

## Roadmap
- [x] API inicial com endpoint `GET /health` e testes
- [x] Ingestão de documentos e segmentação de texto
- [ ] Busca semântica com embeddings
- [ ] Endpoint de perguntas com fontes
- [ ] Avaliação e observabilidade
- [ ] Docker, CI e demonstração

## Stack planejada
Python, FastAPI, pytest, Docker, GitHub Actions e componentes de RAG a selecionar após testes.

## Princípios
- Não utilizar dados confidenciais ou documentos internos de empresas.
- Não registrar segredos ou chaves de API no repositório.
- Diferenciar claramente resultados implementados de funcionalidades planejadas.
- Documentar decisões técnicas e limitações.

## Funcionalidades implementadas

- API FastAPI com verificação de saúde.
- Processamento de arquivos `.txt` em UTF-8, com ou sem BOM.
- Validação de extensão, conteúdo e tamanho máximo de 1 MiB.
- Segmentação em trechos de até 100 palavras, com sobreposição de 20.
- Identificação do documento pelo SHA-256 dos bytes enviados.
- Testes automatizados de saúde, segmentação e ingestão.
- Workflow de testes no GitHub Actions.
- Persistência de documentos e trechos em SQLite.
- Consulta de documentos pelo identificador.
- Módulo de embeddings com o modelo multilingual-e5-small, executado em CPU.
- Validação de entradas vazias e do limite de tokens antes da geração de embeddings.

## Ambiente

Python 3.12 ou superior. O armazenamento utiliza a opção `autocommit`
do módulo SQLite, disponível a partir do Python 3.12.

Para executar os embeddings em CPU, instale o PyTorch no ambiente
virtual antes de instalar o `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

## Embeddings

O módulo `app/embeddings.py` utiliza o modelo pré-treinado
[intfloat/multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small).

- `embed_query` representa perguntas com o prefixo `query:`.
- `embed_passages` representa trechos com o prefixo `passage:`.
- Os vetores são normalizados e possuem 384 dimensões.
- Entradas acima do limite do modelo são rejeitadas para evitar truncamento silencioso.
- O modelo é carregado sob demanda e reutilizado nas chamadas seguintes do processo.
- A primeira execução precisa baixar os arquivos do modelo.

Os testes automatizados do módulo usam um modelo simulado e não
dependem de downloads. Eles verificam validação, prefixos, ordem dos
trechos e limites de tokens. A qualidade da recuperação semântica
ainda precisa de uma avaliação própria.

Os documentos ficam em `data/documents.sqlite3`. Os arquivos locais
do banco são excluídos do versionamento pelo `.gitignore`.

## Executar localmente no Windows

Na pasta do projeto, crie o ambiente virtual e instale as dependências:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Inicie a API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Acesse a documentação interativa em http://127.0.0.1:8000/docs.

## Executar os testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Endpoints

| Método | Rota | Função |
|---|---|---|
| GET | `/health` | Retorna `{"status": "ok"}`. |
| POST | `/documents` | Recebe, segmenta e persiste um documento. |
| GET | `/documents/{document_id}` | Consulta um documento persistido; retorna 404 se não existir. |

### Enviar um documento

Na documentação interativa, abra `POST /documents`, clique em
`Try it out`, selecione um `.txt` no campo `file` e clique em `Execute`.

O envio utiliza `multipart/form-data`.

A resposta contém:

- `document_id`: SHA-256 dos bytes do arquivo.
- `filename`: nome do arquivo enviado.
- `chunk_count`: quantidade de trechos.
- `chunks`: lista de trechos com `index` e `text`.

### Respostas do processamento

| Código | Significado |
|---|---|
| 200 | Documento processado. |
| 400 | Conteúdo vazio, UTF-8 inválido ou presença de caractere nulo. |
| 413 | Arquivo maior que 1 MiB, equivalente a 1.048.576 bytes. |
| 415 | Extensão diferente de `.txt`. |
| 422 | Campo obrigatório ausente ou requisição incompatível. |

## Limitações atuais

Os documentos e seus trechos são persistidos em SQLite. O módulo de
embeddings está implementado e foi exercitado localmente com o modelo
real, mas ainda não está conectado aos endpoints nem ao armazenamento.
Ainda não há indexação vetorial, endpoint de busca semântica ou geração
de respostas com LLM.

## Autor
[Lucas Miranda](https://github.com/itslucasmiranda)
