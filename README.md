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
- [ ] API inicial com endpoint `GET /health` e testes
- [ ] Ingestão de documentos e segmentação de texto
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

## Autor
[Lucas Miranda](https://github.com/itslucasmiranda)
