# Demonstração da v1

## Dois casos em um comando

Com dependências instaladas e `.groq-key` configurado na raiz:

```powershell
.\.venv\Scripts\python.exe -m scripts.demo_rag
```

O script usa um banco temporário e os modelos reais para mostrar uma resposta com fontes e uma pergunta sobre preço ausente nos documentos. Não precisa iniciar a API e não modifica o banco da aplicação. Pode baixar embeddings na primeira execução e consome até duas chamadas à Groq. O código de saída é 1 se houver falha ou se o status divergir do esperado.

## Demonstração pela API

1. Inicie a API e abra `http://127.0.0.1:8000/docs`.
2. Em `POST /documents`, clique em **Try it out**, selecione `examples/armazenamento.txt` no campo `file` e clique em **Execute**.
3. Copie o `document_id` da resposta do upload. O identificador depende dos bytes do arquivo; não copie um ID antigo de outra instalação.
4. Em `POST /ask`, execute:

```json
{
  "query": "Onde ficam salvos os documentos?",
  "top_k": 3,
  "document_id": "SUBSTITUA_PELO_ID_RETORNADO_NO_UPLOAD"
}
```

A resposta esperada é `answered`, com uma explicação sobre SQLite e uma fonte do arquivo enviado. A redação pode variar.

5. Mantenha o mesmo identificador e altere a pergunta para `Qual é o preço mensal da assinatura deste sistema?`. O comportamento esperado é `insufficient_context`, com `sources: []`.
6. Consulte `GET /documents/{document_id}`, reinicie a API e consulte novamente para demonstrar persistência.

## Roteiro de apresentação

- Apresente o problema: consultar documentos e identificar a origem da resposta.
- Mostre upload, pergunta respondida e fontes retornadas.
- Mostre a recusa quando o documento não contém a informação.
- Explique a arquitetura: FastAPI, SQLite, embeddings locais e geração remota.
- Mostre testes e avaliações, distinguindo métricas de recuperação, métricas de status/fontes e revisão humana de fidelidade.
- Declare os limites: dados sintéticos, pequena escala, dependência do provedor e ausência de autenticação para uso público.
