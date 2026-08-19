@echo off
REM ===========================================================================
REM  FinanceAI - lanzador para Windows
REM
REM  Abre los tres servicios en tres ventanas y luego el navegador.
REM  Doble clic sobre este archivo, o "iniciar.cmd" desde cmd.
REM
REM  Para pararlo: cierra las tres ventanas.
REM ===========================================================================
setlocal
title FinanceAI - lanzador
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"

REM --- Entorno de Python -----------------------------------------------------
if not exist "%PY%" (
  echo.
  echo   No existe el entorno virtual .venv
  echo.
  echo   Crealo con estos dos comandos y vuelve a ejecutar iniciar.cmd:
  echo.
  echo     python -m venv .venv
  echo     .venv\Scripts\python.exe -m pip install -r srv-python\requirements.txt
  echo.
  pause
  exit /b 1
)

REM --- Java ------------------------------------------------------------------
REM No hace falta Maven instalado: mvnw.cmd se lo descarga solo la primera vez.
where java >nul 2>&1
if errorlevel 1 (
  echo.
  echo   No se encuentra Java en el PATH. Hace falta JDK 25.
  echo.
  pause
  exit /b 1
)

echo.
echo   Levantando FinanceAI...
echo.
echo     ml-service  http://localhost:8000/docs
echo     API         http://localhost:8080/swagger-ui.html
echo     Frontend    http://localhost:8081
echo.
echo   La primera vez, el backend tarda un poco: mvnw descarga Maven
echo   y las dependencias.
echo.

REM  "cmd /s /k" deja la ventana abierta aunque el proceso falle. El /s hace
REM  que cmd tome el resto de la linea tal cual, necesario si la ruta lleva
REM  espacios.
start "FinanceAI - ml-service (:8000)" /d "%~dp0srv-python" cmd /s /k ""%PY%" -m uvicorn app.main:app --port 8000"

start "FinanceAI - API (:8080)" /d "%~dp0srv-java" cmd /s /k ""%~dp0srv-java\mvnw.cmd" spring-boot:run"

start "FinanceAI - web (:8081)" /d "%~dp0web" cmd /s /k ""%PY%" -m http.server 8081"

REM  Margen para que arranque el backend antes de abrir el navegador.
timeout /t 12 >nul
start "" http://localhost:8081

endlocal
