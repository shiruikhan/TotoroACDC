import os
import time
import requests
from dotenv import load_dotenv
from logger import logger
from token_refresh import renovar_token

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://www.bling.com.br/Api/v3")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "20"))
DETAILS_DELAY = float(os.getenv("DETAILS_DELAY", "0.3"))

_TOKEN = os.getenv("BLING_ACCESS_TOKEN") or ""

def _auth_headers(token: str):
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

def _get_with_refresh(url: str):
    global _TOKEN
    headers = _auth_headers(_TOKEN)
    try:
        resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
    except requests.RequestException as e:
        logger.error("HTTP error fetching details: %s", str(e))
        return None
    if resp.status_code == 401:
        new_token = renovar_token()
        if not new_token:
            logger.error("Token refresh failed while fetching details")
            return None
        _TOKEN = new_token
        headers = _auth_headers(_TOKEN)
        try:
            resp = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
        except requests.RequestException as e:
            logger.error("HTTP error after token refresh: %s", str(e))
            return None
    return resp

def _safe_float(value):
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

def update_product_details(cursor, produto_basico: dict, table_name: str = "temp_produtos_bling") -> bool:
    """Fetch details for a product and update fixed columns in temp_produtos_bling.
    Returns True if an update was executed, else False."""
    # Only for simple physical products
    if produto_basico.get("tipo") != "P" or produto_basico.get("formato") != "S":
        return False

    produto_id = produto_basico.get("id") or produto_basico.get("id_bling")
    if not produto_id:
        return False

    url = f"{API_BASE_URL}/produtos/{produto_id}"
    resp = _get_with_refresh(url)
    if resp is None:
        return False
    if resp.status_code != 200:
        logger.error("Details API error for id=%s status=%s body=%s", produto_id, resp.status_code, resp.text[:300])
        return False

    try:
        data = resp.json().get("data", {})
    except ValueError:
        logger.error("Details API returned non JSON for id=%s", produto_id)
        return False

    dimensoes = data.get("dimensoes") or {}
    midia = data.get("midia") or {}
    imagens = (midia.get("imagens") or {}).get("internas") or []

    imagem = "img/imagem_indisponivel.png"
    if isinstance(imagens, list) and imagens:
        first = imagens[0] or {}
        imagem = first.get("link") or imagem

    largura = _safe_float(dimensoes.get("largura"))
    altura = _safe_float(dimensoes.get("altura"))
    profundidade = _safe_float(dimensoes.get("profundidade"))
    peso_liquido = _safe_float(data.get("pesoLiquido"))
    peso_bruto = _safe_float(data.get("pesoBruto"))
    situacao = data.get("situacao") or produto_basico.get("situacao")

    # codigo is the PK of temp_produtos_bling
    codigo = (produto_basico.get("codigo") or data.get("codigo") or "").strip()
    if not codigo:
        logger.error("Missing codigo when updating details for id=%s", produto_id)
        return False

    sql = f"""            UPDATE {table_name}
           SET largura = %s,
               altura = %s,
               profundidade = %s,
               peso_liquido = %s,
               peso_bruto = %s,
               imagem = %s,
               situacao = %s,
               data_alteracao = NOW()
         WHERE id_bling = %s
    """
    params = (largura, altura, profundidade, peso_liquido, peso_bruto, imagem, situacao, codigo)
    cursor.execute(sql, params)

    time.sleep(DETAILS_DELAY)
    return True
