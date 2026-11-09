import os
import re
from pathlib import Path
from time import perf_counter

import httpx


MODEL = "openai/gpt-oss-20b"
URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqCheckError(RuntimeError):
    pass


def safe_text(value: str, api_key: str) -> str:
    if api_key:
        value = value.replace(api_key, "[CHAVE OCULTA]")
    value = re.sub(r"gsk_[A-Za-z0-9_-]+", "[CHAVE OCULTA]", value)
    value = re.sub(r"(?i)Bearer\s+[^\s<>\"']+", "Bearer [OCULTO]", value)
    value = " ".join(value.split())
    return "".join(char for char in value if char.isprintable())[:1000]


def provider_error(response: httpx.Response, api_key: str) -> str:
    fallback = (
        "Formato: " + safe_text(response.headers.get("content-type", "nao informado"), api_key)
        + " | Corpo: " + (safe_text(response.text, api_key) or "[vazio]")
    )
    try:
        payload = response.json()
    except ValueError:
        return fallback
    if not isinstance(payload, dict):
        return fallback
    error = payload.get("error")
    if not isinstance(error, dict):
        return fallback
    details = []
    for field in ("code", "type", "message"):
        value = error.get(field)
        if isinstance(value, str) and value.strip():
            details.append(f"{field}: {safe_text(value, api_key)}")
    return " | ".join(details) or fallback


def request_answer(client: httpx.Client, api_key: str) -> str:
    try:
        response = client.post(
            URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": "Explique em portugues, em duas frases, o que e uma API.",
                    }
                ],
                "reasoning_effort": "low",
                "include_reasoning": False,
                "max_completion_tokens": 1024,
                "stream": False,
            },
        )
    except httpx.TimeoutException:
        raise GroqCheckError("Tempo de espera esgotado ao acessar a Groq.") from None
    except httpx.RequestError:
        raise GroqCheckError("Falha de conexao com a Groq.") from None

    if response.status_code != 200:
        explanations = {
            400: "Requisicao rejeitada pelo provedor.",
            401: "Chave ausente, invalida ou revogada.",
            403: "A conta ou o projeto nao tem permissao para esta chamada.",
            404: "Modelo ou endpoint indisponivel.",
            429: "Limite de uso atingido. Confira os limites da conta.",
        }
        detail = explanations.get(response.status_code, "Falha retornada pelo provedor.")
        diagnostic = provider_error(response, api_key)
        if diagnostic:
            detail += f"\nDetalhe da resposta: {diagnostic}"
        raise GroqCheckError(f"HTTP {response.status_code}: {detail}")

    try:
        choice = response.json()["choices"][0]
        answer = choice["message"]["content"]
        finish_reason = choice["finish_reason"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise GroqCheckError("A Groq retornou uma resposta em formato inesperado.") from None

    if finish_reason != "stop":
        raise GroqCheckError("A resposta nao foi concluida normalmente.")
    if not isinstance(answer, str) or not answer.strip():
        raise GroqCheckError("A Groq retornou uma resposta vazia.")

    return answer.strip()


def main() -> int:
    print("Diagnostico Groq: chave em arquivo local", flush=True)
    key_path = Path(__file__).resolve().parent.parent / ".groq-key"
    try:
        api_key = key_path.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        print("Crie o arquivo .groq-key na raiz do projeto com a chave completa.")
        return 1
    except (OSError, UnicodeError):
        print("Nao foi possivel ler .groq-key como texto UTF-8.")
        return 1
    if not api_key:
        print("Configure GROQ_API_KEY neste terminal antes de executar.")
        return 1
    if not re.fullmatch(r"gsk_[A-Za-z0-9_-]+", api_key):
        print("ERRO: a entrada nao tem o formato esperado de uma chave Groq.")
        print("Configure novamente a variavel usando a chave completa, sem aspas.")
        return 1

    print(f"Consultando {MODEL} pela Groq...", flush=True)
    started = perf_counter()
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            answer = request_answer(client, api_key)
    except GroqCheckError as exc:
        print(f"ERRO: {exc}")
        return 1

    print(answer)
    print(f"Tempo total da chamada: {perf_counter() - started:.2f}s")
    print("OK: autenticacao e geracao de texto pela Groq.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
