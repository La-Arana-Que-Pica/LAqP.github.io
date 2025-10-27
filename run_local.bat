@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel% neq 0 (set PY=python) else (set PY=py -3)

echo [1/4] Validando CSV...
%PY% manage_db.py validate

echo [2/4] Exportando JSON...
%PY% manage_db.py export

echo [3/4] Generando paginas de jugadores...
%PY% manage_db.py build

echo [4/4] Iniciando servidor en http://localhost:8000  (Ctrl+C para parar)
%PY% -m http.server 8000