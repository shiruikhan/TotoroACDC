import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Iterable

import requests
import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

# ----------------------------------------------------------------------------
# Boot: load env and configure logging
# ----------------------------------------------------------------------------
load_dotenv()

LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, f"temp_produtos_{datetime.now().strftime('%Y-%m-%d')}.log"),
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
if os.getenv("LOG_TO_CONSOLE", "0").lower() in {"1", "true", "yes"}:
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(ch)

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", ""),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", ""),
    "port": int(os.getenv("DB_PORT", "3306")),
}

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.bling.com.br/Api/v3")
AUTH_BASE64 = os.getenv("BLING_AUTH_BASE64", "")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
MAX_RETRY = int(os.getenv("MAX_RETRY", "3"))
DELAY_OK = float(os.getenv("DELAY_OK", "1.0"))
DELAY_FAIL = float(os.getenv("DELAY_FAIL", "5.0"))
LIMITE_POR_PAGINA = int(os.getenv("BLING_LIMIT", "100"))
SITUACAO = os.getenv("BLING_SITUACAO", "A")
TIPO = os.getenv("BLING_TIPO", "P")

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def _validar_db_config() -> None:
    faltantes = [k for k, v in DB_CONFIG.items() if k in {"host","user","password","database"} and not v]
    if faltantes:
        raise RuntimeError(f"Variáveis de ambiente de banco ausentes: {', '.join(faltantes)}")


def atualizar_tokens() -> None:
    """Atualiza access/refresh tokens no banco usando o refresh token atual."""
    _validar_db_config()
    if not AUTH_BASE64:
        raise RuntimeError("Credenciais OAuth (BLING_AUTH_BASE64) não definidas")

    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute("SELECT valor FROM configuracoes_api WHERE chave = 'bling_refresh_token' LIMIT 1")
            row = cur.fetchone()
            if not row or not row["valor"]:
                raise RuntimeError("Refresh Token não encontrado no banco")
            refresh_token = row["valor"]

    url = f"{API_BASE_URL}/oauth/token"
    headers = {
        "Authorization": f"Basic {AUTH_BASE64}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    try:
        resp = requests.post(url, headers=headers, data=payload, timeout=HTTP_TIMEOUT)
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"Falha na requisição de token: {e}")

    if resp.status_code != 200 or "access_token" not in data or "refresh_token" not in data:
        raise RuntimeError(f"Resposta inválida do Bling: {resp.status_code} - {data}")

    new_access = data["access_token"]
    new_refresh = data["refresh_token"]
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE configuracoes_api SET valor=%s WHERE chave='bling_access_token'",
                (new_access,),
            )
            cur.execute(
                "UPDATE configuracoes_api SET valor=%s WHERE chave='bling_refresh_token'",
                (new_refresh,),
            )
            conn.commit()
    logging.info("Tokens atualizados com sucesso")


def _buscar_access_token() -> str:
    _validar_db_config()
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT valor FROM configuracoes_api WHERE chave='bling_access_token' LIMIT 1")
            row = cur.fetchone()
            if row and row[0]:
                return row[0].strip()
    raise RuntimeError("Access Token não encontrado no banco")


def _session_bling(token: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/json"})
    return s


# ----------------------------------------------------------------------------
# API paging
# ----------------------------------------------------------------------------
def iter_produtos(sess: requests.Session) -> Iterable[Dict[str, Any]]:
    pagina = 1
    while True:
        url = f"{API_BASE_URL}/produtos"
        params = {"pagina": pagina, "limite": LIMITE_POR_PAGINA, "tipo": TIPO, "situacao": SITUACAO}
        for tentativa in range(1, MAX_RETRY + 1):
            try:
                resp = sess.get(url, params=params, timeout=HTTP_TIMEOUT)
                if resp.status_code == 200:
                    payload = resp.json()
                    data = payload.get("data", []) or []
                    if not data:
                        logging.info("Fim da paginação: página %s vazia", pagina)
                        return
                    for p in data:
                        yield {
                            "id": p.get("id"),
                            "codigo": p.get("codigo"),
                            "nome": p.get("nome"),
                            "preco": p.get("preco", 0),
                            "estoque": (p.get("estoque") or {}).get("saldoVirtualTotal", 0),
                        }
                    pagina += 1
                    time.sleep(DELAY_OK)
                    break
                elif resp.status_code in (429, 500, 502, 503, 504):
                    logging.warning("HTTP %s na página %s (tentativa %s/%s)", resp.status_code, pagina, tentativa, MAX_RETRY)
                    time.sleep(DELAY_FAIL)
                    continue
                else:
                    logging.error("Falha %s na página %s: %s", resp.status_code, pagina, resp.text[:300])
                    return
            except requests.RequestException as e:
                logging.error("Exceção de rede na página %s (tentativa %s/%s): %s", pagina, tentativa, MAX_RETRY, e)
                time.sleep(DELAY_FAIL)
                continue


# ----------------------------------------------------------------------------
# DB update
# ----------------------------------------------------------------------------
def atualizar_temp_produtos(sess: requests.Session) -> Dict[str, int]:
    """Atualiza tabela temp_produtos_bling com preços e estoques atuais."""
    _validar_db_config()
    stats = {"processados": 0, "gravados": 0}
    with mysql.connector.connect(**DB_CONFIG) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            for prod in iter_produtos(sess):
                stats["processados"] += 1
                cur.execute(
                    """
                    INSERT INTO temp_produtos_bling (id_bling, codigo, nome, preco, estoque)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        nome=VALUES(nome), preco=VALUES(preco), estoque=VALUES(estoque)
                    """,
                    (prod["id"], prod["codigo"], prod["nome"], prod["preco"], prod["estoque"]),
                )
                if cur.rowcount:
                    stats["gravados"] += 1
                if stats["processados"] % 200 == 0:
                    conn.commit()
            conn.commit()
    logging.info("Atualização concluída: %s", stats)
    return stats


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> None:
    try:
        atualizar_tokens()
        token = _buscar_access_token()
        sess = _session_bling(token)
        atualizar_temp_produtos(sess)
        logging.info("Processo finalizado com sucesso")
    except Exception as e:
        logging.critical("Erro fatal: %s", e)
        raise


if __name__ == "__main__":
    main()