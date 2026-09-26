@echo off
cd /d "%~dp0"
python --version >nul 2>&1
if not errorlevel 1 (
    python app.py --open-browser
) else (
    py --version >nul 2>&1
    if not errorlevel 1 (
        py app.py --open-browser
    ) else (
        echo Python nao encontrado. Instale Python 3.10 ou superior e tente novamente.
    )
)
pause
