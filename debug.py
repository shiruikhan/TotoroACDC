import os
import sys
import time

print("🚀 Início da execução")
print(f"🧠 Versão do Python: {sys.version}")
print(f"📁 Diretório atual: {os.getcwd()}")
print(f"📄 Nome do arquivo: {__file__}")
print(f"🛠 Executável: {sys.executable}")

print("⏳ Esperando 2 segundos...")
time.sleep(2)

print("✅ Etapa 1 concluída")

# Teste de acesso a variável de ambiente
from dotenv import load_dotenv
load_dotenv()

bling_token = os.getenv("BLING_ACCESS_TOKEN")
if bling_token:
    print("🔐 Token de acesso carregado com sucesso.")
else:
    print("⚠️ Token de acesso NÃO encontrado no .env")

# Teste de importação de função
try:
    from db import conectar_mysql
    print("🗃️ Módulo de banco importado com sucesso.")
except Exception as e:
    print("❌ Erro ao importar módulo de banco:", e)

print("🏁 Fim da execução de diagnóstico.")
