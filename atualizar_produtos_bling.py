
import os
import json
import time
import logging
from datetime import datetime

import requests
import mysql.connector
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Carrega variáveis de ambiente do .env (se existir)
# ---------------------------------------------------------------------------
load_dotenv()

# ---------------------------------------------------------------------------
# Configurações via variáveis de ambiente (.env)
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", ""),
    "port": int(os.getenv("DB_PORT", "3306")),
}

# Caminhos de saída
JSON_PATH = os.getenv("JSON_PATH", "produtos_bling.json")
FALHAS_PATH = os.getenv("FALHAS_PATH", "falhas_bling.json")

# Parâmetros de execução
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
DELAY_OK = float(os.getenv("DELAY_OK", "1.0"))
DELAY_FAIL = float(os.getenv("DELAY_FAIL", "5.0"))
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.bling.com.br/Api/v3")

# Logging
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, f"bling_exec_{datetime.now().strftime('%Y-%m-%d')}.log"),
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)

# ---------------------------------------------------------------------------
# Funções
# ---------------------------------------------------------------------------
def _validar_db_config():
    faltantes = [k for k, v in DB_CONFIG.items() if k in {"host","user","password","database"} and not v]
    if faltantes:
        raise RuntimeError(f"Variáveis de ambiente de banco ausentes: {', '.join(faltantes)}")

def buscar_access_token():
    """Busca o access token no banco (tabela configuracoes_api, chave = 'bling_access_token')."""
    _validar_db_config()
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT valor FROM configuracoes_api WHERE chave = 'bling_access_token'")
            row = cursor.fetchone()
            if row and row[0]:
                return row[0].strip()
            raise RuntimeError("Access Token não encontrado no banco.")

def buscar_ids_produtos(headers):
    ids = []
    pagina = 1
    while True:
        url = f"{API_BASE_URL}/produtos?pagina={pagina}"
        try:
            resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            if resp.status_code != 200:
                logging.error("Erro página %s: %s - %s", pagina, resp.status_code, resp.text)
                break

            data = resp.json().get("data", [])
            if not data:
                break

            for item in data:
                if item.get("tipo") == "P" and item.get("formato") == "S":
                    ids.append(item.get("id"))

            if len(data) < 100:
                break
            pagina += 1
            time.sleep(DELAY_OK)
        except Exception as e:
            logging.error("Falha ao buscar IDs na página %s: %s", pagina, e)
            break
    return ids

def buscar_detalhes_produto(produto_id, headers):
    url = f"{API_BASE_URL}/produtos/{produto_id}"
    for tentativa in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                if data.get("tipo") != "P" or data.get("formato") != "S":
                    return None
                return {
                    "codigo": data.get("codigo", ""),
                    "nome": data.get("nome", ""),
                    "preco": data.get("preco", 0),
                    "estoque": data.get("estoque", {}).get("saldoVirtualTotal", 0),
                    "largura": data.get("dimensoes", {}).get("largura"),
                    "altura": data.get("dimensoes", {}).get("altura"),
                    "profundidade": data.get("dimensoes", {}).get("profundidade"),
                    "peso_liquido": data.get("pesoLiquido"),
                    "peso_bruto": data.get("pesoBruto"),
                    "imagem": (
                        data.get("midia", {}).get("imagens", {}).get("internas", [{}])[0].get("link")
                        if data.get("midia", {}).get("imagens", {}).get("internas") else "img/imagem_indisponivel.png"
                    ) or "img/imagem_indisponivel.png",
                    "situacao": data.get("situacao", "A"),
                }
            elif resp.status_code == 504:
                logging.warning("504 Timeout ao buscar produto %s, tentativa %s/%s", produto_id, tentativa, MAX_RETRY)
            else:
                logging.error("Erro %s ao buscar produto %s: %s", resp.status_code, produto_id, resp.text)
                break
        except Exception as e:
            logging.error("Exception ao buscar produto %s: %s", produto_id, e)
        time.sleep(DELAY_FAIL)
    return None

def gerar_json_produtos(headers):
    logging.info("Buscando IDs dos produtos tipo P e formato S...")
    ids = buscar_ids_produtos(headers)
    logging.info("Total de produtos filtrados: %s", len(ids))

    produtos = []
    falhas = []
    for i, pid in enumerate(ids, 1):
        logging.info("[%s/%s] Coletando produto ID %s", i, len(ids), pid)
        produto = buscar_detalhes_produto(pid, headers)
        if produto:
            produtos.append(produto)
        else:
            falhas.append(pid)
        time.sleep(DELAY_OK)

    if falhas:
        logging.info("Tentando novamente %s produtos que falharam...", len(falhas))
        segunda_falha = []
        for pid in falhas:
            logging.info("[Retry] Coletando produto ID %s", pid)
            produto = buscar_detalhes_produto(pid, headers)
            if produto:
                produtos.append(produto)
            else:
                segunda_falha.append(pid)
            time.sleep(DELAY_OK)
        falhas = segunda_falha

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    logging.info("JSON salvo como: %s", JSON_PATH)

    if falhas:
        with open(FALHAS_PATH, "w", encoding="utf-8") as f:
            json.dump(falhas, f, ensure_ascii=False, indent=2)
        logging.warning("Falhas persistentes: %s produtos. IDs salvos em %s", len(falhas), FALHAS_PATH)

def importar_para_banco():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        produtos = json.load(f)

    _validar_db_config()
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor(dictionary=True) as cursor:
            total_inseridos = 0
            total_atualizados = 0
            total_iguais = 0
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for produto in produtos:
                cursor.execute("SELECT * FROM produtos_bling WHERE codigo = %s", (produto["codigo"],))
                row = cursor.fetchone()

                campos = [
                    "nome", "preco", "estoque", "largura", "altura", "profundidade",
                    "peso_liquido", "peso_bruto", "imagem", "situacao"
                ]
                valores_novos = [produto.get(c) for c in campos]

                if row:
                    alterado = any(str(row.get(campo)) != str(produto.get(campo)) for campo in campos)
                    if alterado:
                        cursor.execute(
                            """
                            UPDATE produtos_bling
                            SET nome = %s, preco = %s, estoque = %s, largura = %s, altura = %s,
                                profundidade = %s, peso_liquido = %s, peso_bruto = %s,
                                imagem = %s, situacao = %s, data_alteracao = %s
                            WHERE codigo = %s
                            """,
                            valores_novos + [now, produto["codigo"]]
                        )
                        total_atualizados += 1
                        logging.info("Atualizado: %s", produto["codigo"])
                    else:
                        total_iguais += 1
                        logging.info("Inalterado: %s", produto["codigo"])
                else:
                    cursor.execute(
                        """
                        INSERT INTO produtos_bling (
                            codigo, nome, preco, estoque, largura, altura, profundidade,
                            peso_liquido, peso_bruto, imagem, situacao, data_alteracao
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [produto["codigo"]] + valores_novos + [now]
                    )
                    total_inseridos += 1
                    logging.info("Inserido: %s", produto["codigo"])

            conn.commit()

    logging.info("Importação finalizada.")
    logging.info("Inseridos: %s, Atualizados: %s, Inalterados: %s", total_inseridos, total_atualizados, total_iguais)

def executar():
    logging.info("Iniciando processo completo...")
    try:
        access_token = buscar_access_token()
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        gerar_json_produtos(headers)
        importar_para_banco()
        logging.info("Processo concluído com sucesso.")
    except Exception as e:
        # Evite vazar segredos nos logs
        logging.critical("Erro fatal: %s", e)

if __name__ == "__main__":
    executar()
