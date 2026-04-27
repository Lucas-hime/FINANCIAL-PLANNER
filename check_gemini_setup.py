import os
import sys


def main() -> int:
    key = os.getenv('GEMINI_API_KEY', '').strip()
    if not key:
        print('❌ GEMINI_API_KEY não foi encontrada. Abra o arquivo .env e preencha sua chave.')
        return 1

    if len(key) < 20 or 'your_gemini_api_key_here' in key.lower():
        print('❌ A GEMINI_API_KEY parece vazia ou de exemplo. Cole uma chave válida no .env.')
        return 1

    try:
        from services.ai_client import AIClientError, generate_financial_response
    except Exception:
        print('❌ Dependências da IA não encontradas. Rode: pip install -r requirements.txt')
        return 1

    try:
        text = generate_financial_response(
            prompt='Responda apenas com a palavra: pronto',
            system_instruction='Você é um assistente objetivo.'
        )
        if not text.strip():
            print('❌ A resposta da IA veio vazia. Tente novamente em alguns segundos.')
            return 1
        print('✅ Integração Gemini OK! O modelo gemini-2.5-flash respondeu com sucesso.')
        return 0
    except AIClientError as exc:
        print(f'❌ Não foi possível validar a integração Gemini: {exc.message}')
        return 1
    except Exception:
        print('❌ Ocorreu uma falha inesperada ao validar Gemini. Tente novamente em instantes.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
