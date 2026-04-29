# Planejador Financeiro Pessoal (Brasil)

Siga exatamente estes passos:

1. Instale o Python: https://www.python.org/downloads/ — marque **"Add Python to PATH"**.
2. Crie sua chave Gemini gratuita: https://aistudio.google.com/apikey — é de graça, sem cartão.
3. Abra o arquivo `.env` e cole sua chave onde indicado.
4. Dê dois cliques em `instalar.bat`.
5. Dê dois cliques em `iniciar.bat` — o app abre sozinho no navegador.

## Verificação rápida da integração Gemini

Depois de preencher a chave no `.env`, rode:

```bash
python check_gemini_setup.py
```

Se aparecer `✅ Integração Gemini OK!`, está tudo pronto para usar os recursos de IA.


## Se aparecer erro de pip

O instalador agora usa `python -m pip` automaticamente. Se ainda falhar, reinstale o Python e marque **Add Python to PATH**.


Se o comando `python` não funcionar no Windows, o instalador e o inicializador tentam automaticamente o launcher `py`.

A instalação usa `pip --user`, então não precisa de permissões de administrador.
