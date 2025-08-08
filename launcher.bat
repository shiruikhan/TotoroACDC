@echo off
setlocal

:: Caminho do Python
set PYTHON_EXE=C:\python\python.exe

:: Caminho do script Python
set SCRIPT_PATH=G:\Projeto API ACDC\atualizar_produtos_bling.py

:: Caminho do arquivo de log (log diário com data no nome)
set LOG_PATH=G:\Projeto API ACDC\bling_log_%DATE:~6,4%-%DATE:~3,2%-%DATE:~0,2%.txt

:: Executa o script com redirecionamento de saída e erro
"%PYTHON_EXE%" "%SCRIPT_PATH%" > "%LOG_PATH%" 2>&1

endlocal
