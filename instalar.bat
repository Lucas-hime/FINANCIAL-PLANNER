@echo off
setlocal

set "PY_CMD=python"

echo ============================================
echo   Instalando seu Planejador Financeiro...
echo ============================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERRO: Python nao encontrado.
        echo Por favor instale o Python em: https://www.python.org/downloads/
        echo Marque a opcao "Add Python to PATH" durante a instalacao.
        pause
        exit /b 1
    )
    set "PY_CMD=py"
)

echo Python encontrado. Verificando pip...
%PY_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Pip nao encontrado. Tentando corrigir automaticamente...
    %PY_CMD% -m ensurepip --upgrade >nul 2>&1
)

%PY_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Nao consegui habilitar o pip automaticamente.
    echo Feche esta janela, reinstale o Python e marque "Add Python to PATH".
    pause
    exit /b 1
)

echo Instalando dependencias...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERRO ao instalar dependencias.
    echo Tente executar novamente com internet ativa.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env
    echo.
    echo IMPORTANTE: Abra o arquivo .env e cole sua chave Gemini gratuita.
    echo Acesse: https://aistudio.google.com/apikey para criar sua chave gratis.
    echo.
)

if not exist data mkdir data

echo.
echo ============================================
echo   Instalacao concluida com sucesso!
echo   Agora execute: iniciar.bat
echo ============================================
pause
