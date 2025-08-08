@echo off
setlocal ENABLEDELAYEDEXPANSION

REM >> AJUSTE AQUI: pasta do projeto e Python
set "APP_HOME=G:\Projeto API ACDC"
set "PYTHON_EXE=C:\Python\python.exe"
set "SCRIPT_NAME=atualiza_simples_nojson.py"

REM Log do launcher (além dos logs do script)
set "LAUNCHER_LOG=%APP_HOME%\launcher_%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%.log"

chcp 65001 >NUL 2>&1

if not exist "%APP_HOME%\%SCRIPT_NAME%" (
  echo [ERRO] Script nao encontrado: "%APP_HOME%\%SCRIPT_NAME%"
  exit /b 2
)
pushd "%APP_HOME%"

echo [INFO] Iniciando %SCRIPT_NAME% com "%PYTHON_EXE%"
"%PYTHON_EXE%" "%APP_HOME%\%SCRIPT_NAME%" > "%LAUNCHER_LOG%" 2>&1
set "ERR=%ERRORLEVEL%"

if not "%ERR%"=="0" (
  echo [ERRO] Execucao terminou com codigo %ERR%. Verifique "%LAUNCHER_LOG%".
) else (
  echo [OK] Execucao concluida. Veja "%LAUNCHER_LOG%" para detalhes.
)

popd
exit /b %ERR%
