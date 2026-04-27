@echo off
setlocal

echo Iniciando seu Planejador Financeiro...
start "" http://localhost:5000

python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ERRO: Python nao encontrado.
        echo Instale em: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    py app.py
    exit /b %errorlevel%
)

python app.py
