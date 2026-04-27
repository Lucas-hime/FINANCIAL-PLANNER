@echo off
echo ============================================
echo   Instalando seu Planejador Financeiro...
echo ============================================
echo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado.
    echo Por favor instale o Python em: https://www.python.org/downloads/
    echo Marque a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)
echo Python encontrado. Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERRO ao instalar dependencias. Tente rodar como Administrador.
    pause
    exit /b 1
)
if not exist .env (
    copy .env.example .env
    echo.
    echo IMPORTANTE: Abra o arquivo .env e cole sua chave Groq gratuita.
    echo Acesse: https://console.groq.com para criar sua chave gratis.
    echo.
)
if not exist data mkdir data
echo.
echo ============================================
echo   Instalacao concluida com sucesso!
echo   Agora execute: iniciar.bat
echo ============================================
pause
