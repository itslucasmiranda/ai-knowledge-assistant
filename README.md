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
| POST | `/documents` | Recebe um arquivo e retorna seus trechos. |

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

Os documentos são processados e devolvidos na resposta, sem persistência
para consultas posteriores. Ainda não há embeddings, busca semântica
ou integração com modelos de linguagem.

A segmentação considera palavras, não tokens, e normaliza espaços e
quebras de linha. Os valores de tamanho e sobreposição ainda precisam
ser avaliados com documentos representativos.

O projeto está preparado para desenvolvimento local. Autenticação e
controles de implantação pública ainda não foram implementados.

## Autor
[Lucas Miranda](https://github.com/itslucasmiranda)
