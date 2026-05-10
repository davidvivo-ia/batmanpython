@echo off
REM ======================================================================
REM  Batman Returns (Python) — one-click launcher for Windows
REM
REM  Doble click sobre este archivo. Hace, en orden:
REM    1. Encuentra Python (3.11+) en PATH.
REM    2. Crea un entorno virtual local en .venv\ si no existe.
REM    3. Instala el juego en modo editable la primera vez.
REM    4. Lanza el juego.
REM ======================================================================

setlocal
cd /d "%~dp0"

REM ---- Find a usable Python ----
set "PYEXE="
for %%P in (py python3.13 python3.12 python3.11 python) do (
    if not defined PYEXE (
        where %%P >nul 2>&1 && set "PYEXE=%%P"
    )
)
if not defined PYEXE (
    echo.
    echo [ERROR] No se encontro Python instalado.
    echo Descargalo desde https://www.python.org/downloads/  (3.11 o superior)
    echo.
    pause
    exit /b 1
)

REM `py` launcher prefers a specific version when available
if "%PYEXE%"=="py" set "PYEXE=py -3"

REM ---- Create venv on first run ----
if not exist ".venv\Scripts\python.exe" (
    echo Primer arranque: creando entorno virtual en .venv\ ...
    %PYEXE% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo Instalando dependencias ^(pygame-ce, numpy^) ...
    ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    ".venv\Scripts\python.exe" -m pip install --quiet -e .
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
)

REM ---- Run the game ----
".venv\Scripts\python.exe" -m batman_returns
endlocal
