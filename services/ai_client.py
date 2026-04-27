import os
from dataclasses import dataclass

from google import genai


MODEL_NAME = 'gemini-2.5-flash'


@dataclass
class AIClientError(Exception):
    code: str
    message: str

    def __str__(self):
        return self.message


def _classify_error(exc: Exception) -> AIClientError:
    msg = str(exc).lower()
    if any(k in msg for k in ['429', 'quota', 'rate limit', 'resource exhausted']):
        return AIClientError('rate_limit', 'Seu limite gratuito da IA foi atingido agora. Tente novamente em alguns minutos.')
    if any(k in msg for k in ['connection', 'timeout', 'network', 'dns', 'temporarily unavailable']):
        return AIClientError('network', 'Não consegui falar com a IA por instabilidade de conexão. Tente novamente em instantes.')
    return AIClientError('unknown', 'Não consegui conversar com a IA agora. Seus dados continuam salvos com segurança.')


def generate_financial_response(prompt: str, system_instruction: str | None = None) -> str:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise AIClientError('missing_api_key', 'Configure sua chave GEMINI_API_KEY no arquivo .env para usar os recursos de IA.')

    try:
        client = genai.Client(api_key=api_key)
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
        )
        text = (response.text or '').strip() if response else ''
        if not text:
            raise AIClientError('empty_response', 'A IA respondeu vazio desta vez. Tente novamente com um pedido mais específico.')
        return text
    except AIClientError:
        raise
    except Exception as exc:
        raise _classify_error(exc)
