
import os
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Carrega .env e configura logging
# ---------------------------------------------------------------------------
load_dotenv()

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, f"atualiza_simples_{datetime.now().strftime('%Y-%m-%d')}.log"),
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)

# (Opcional) também logar no console: útil em execução local
if os.getenv("LOG_TO_CONSOLE", "0") in {"1", "true", "TRUE"}:
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(console)

# ---------------------------------------------------------------------------
# Configurações via .env
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", ""),
    "port": int(os.getenv("DB_PORT", "3306")),
}

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.bling.com.br/Api/v3")
JSON_PATH = os.getenv("JSON_PATH", "produtos_bling_api.json")

LIMITE_POR_PAGINA = int(os.getenv("BLING_LIMIT", "100"))
SITUACAO = os.getenv("BLING_SITUACAO", "A")  # A=Ativo
TIPO = os.getenv("BLING_TIPO", "P")          # P=Produto
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
DELAY_OK = float(os.getenv("DELAY_OK", "1.0"))
DELAY_FAIL = float(os.getenv("DELAY_FAIL", "5.0"))

# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def _validar_db_config() -> None:
    faltantes = [k for k, v in DB_CONFIG.items() if k in {"host","user","password","database"} and not v]
    if faltantes:
        raise RuntimeError(f"Variáveis de ambiente de banco ausentes: {', '.join(faltantes)}")

def _buscar_access_token() -> str:
    """Busca o token na tabela configuracoes_api (chave 'bling_access_token')."""
    _validar_db_config()
    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT valor FROM configuracoes_api WHERE chave = 'bling_access_token' LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0].strip()
    except MySQLError as e:
        logging.critical("Erro ao buscar token no banco: %s", e)
        raise
    raise RuntimeError("Access Token não encontrado no banco.")

def _session_bling(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    return s

# ---------------------------------------------------------------------------
# Coleta de produtos (Bling)
# ---------------------------------------------------------------------------
def coletar_produtos_bling() -> List[Dict[str, Any]]:
    token = _buscar_access_token()
    sess = _session_bling(token)

    produtos: List[Dict[str, Any]] = []
    pagina = 1
    logging.info("Iniciando coleta dos produtos do Bling...")

    while True:
        url = f"{API_BASE_URL}/produtos"
        params = {
            "pagina": pagina,
            "limite": LIMITE_POR_PAGINA,
            "tipo": TIPO,
            "situacao": SITUACAO,
        }
        for tentativa in range(1, MAX_RETRY + 1):
            try:
                resp = sess.get(url, params=params, timeout=HTTP_TIMEOUT)
                if resp.status_code == 200:
                    payload = resp.json()
                    itens = payload.get("data", [])
                    if not itens:
                        logging.info("Sem mais itens. Fim da coleta. Página %s.", pagina)
                        # Salva JSON e retorna
                        with open(JSON_PATH, "w", encoding="utf-8") as f:
                            json.dump(produtos, f, ensure_ascii=False, indent=2)
                        logging.info("Total coletado: %s. JSON salvo em %s", len(produtos), JSON_PATH)
                        return produtos

                    # Mapeamento enxuto
                    lote = [{
                        "id": p.get("id"),
                        "codigo": p.get("codigo"),
                        "nome": p.get("nome"),
                        "preco": p.get("preco", 0),
                        "estoque": (p.get("estoque") or {}).get("saldoVirtualTotal", 0),
                    } for p in itens]

                    produtos.extend(lote)
                    logging.info("Página %s coletada: %s itens (total %s).", pagina, len(itens), len(produtos))

                    # Se veio menos que o limite, provavelmente acabou
                    if len(itens) < LIMITE_POR_PAGINA:
                        with open(JSON_PATH, "w", encoding="utf-8") as f:
                            json.dump(produtos, f, ensure_ascii=False, indent=2)
                        logging.info("Coleta encerrada por término de itens. Total: %s. JSON: %s", len(produtos), JSON_PATH)
                        return produtos

                    pagina += 1
                    time.sleep(DELAY_OK)
                    break  # sai do laço de retry para próxima página

                elif resp.status_code in (429, 500, 502, 503, 504):
                    logging.warning("HTTP %s na página %s (tentativa %s/%s). Conteúdo: %s",
                                    resp.status_code, pagina, tentativa, MAX_RETRY, resp.text[:300])
                    time.sleep(DELAY_FAIL)
                    continue
                else:
                    logging.error("Falha %s ao coletar página %s: %s", resp.status_code, pagina, resp.text[:300])
                    # Encerra a coleta em erro não recuperável
                    with open(JSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(produtos, f, ensure_ascii=False, indent=2)
                    return produtos
            except requests.RequestException as e:
                logging.error("Exceção de rede na página %s (tentativa %s/%s): %s", pagina, tentativa, MAX_RETRY, e)
                time.sleep(DELAY_FAIL)
                continue

# ---------------------------------------------------------------------------
# Atualização no banco
# ---------------------------------------------------------------------------
def atualizar_banco(produtos: List[Dict[str, Any]]) -> Dict[str, int]:
    _validar_db_config()
    stats = {"processados": 0, "atualizados": 0, "nao_encontrados": 0}

    try:
        with mysql.connector.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                total = len(produtos)
                logging.info("Iniciando atualização no banco. Total a processar: %s", total)
                for idx, prod in enumerate(produtos, start=1):
                    stats["processados"] += 1
                    cursor.execute(
                        """
                        UPDATE produtos_bling
                           SET nome = %s,
                               preco = %s,
                               estoque = %s
                         WHERE id_bling = %s
                        """,
                        (prod["nome"], prod["preco"], prod["estoque"], prod["id"]),
                    )
                    if cursor.rowcount > 0:
                        stats["atualizados"] += 1
                        logging.debug("[%(i)d/%(t)d] Atualizado id_bling=%(id)s codigo=%(cod)s",
                                      {"i": idx, "t": total, "id": prod["id"], "cod": prod["codigo"]})
                    else:
                        stats["nao_encontrados"] += 1
                        logging.debug("[%(i)d/%(t)d] Não encontrado id_bling=%(id)s codigo=%(cod)s",
                                      {"i": idx, "t": total, "id": prod["id"], "cod": prod["codigo"]})
                conn.commit()
    except MySQLError as e:
        logging.critical("Erro MySQL durante atualização: %s", e)
        raise

    logging.info("Atualização concluída. Stats: %s", stats)
    return stats

# ---------------------------------------------------------------------------
# Execução principal
# ---------------------------------------------------------------------------
def main() -> None:
    try:
        produtos = coletar_produtos_bling()
        stats = atualizar_banco(produtos)
        logging.info("Processo finalizado com sucesso. %s", stats)
    except Exception as e:
        # Não vazar segredos
        logging.critical("Erro fatal: %s", e)
        raise

if __name__ == "__main__":
    main()
