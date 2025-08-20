import os
import time
import random
import requests
from dotenv import load_dotenv
from logger import logger
from token_refresh import renovar_token

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "https://www.bling.com.br/Api/v3")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "30"))
MAX_RETRIES_429 = int(os.getenv("MAX_RETRIES_429", "5"))

def _auth_headers() -> dict:
    token = os.getenv("BLING_ACCESS_TOKEN")
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

def _sleep_retry_after(resp, attempt: int):
    ra = resp.headers.get("Retry-After")
    if ra and ra.isdigit():
        delay = int(ra)
    else:
        delay = min(2 ** attempt, 30) + random.uniform(0, 0.5)
    logger.warning("429 recebido. Aguardando %.2fs (tentativa %s).", delay, attempt)
    time.sleep(delay)

def _request_with_refresh(method: str, url: str, **kwargs):
    max_retries = 3  # Número máximo de tentativas para renovar o token
    retry_count = 0

    while retry_count < max_retries:
        try:
            resp = requests.request(method, url, timeout=HTTP_TIMEOUT, headers=_auth_headers(), **kwargs)
            
            # Se a resposta for bem-sucedida, retorna imediatamente
            if resp.status_code == 200:
                return resp

            # Tratamento de token expirado
            if resp.status_code == 401:
                logger.warning("Token expirado. Tentativa %d de %d de renovação...", retry_count + 1, max_retries)
                new_token = renovar_token()
                if new_token:
                    retry_count += 1
                    continue  # Tenta a requisição novamente com o novo token
                else:
                    logger.error("Falha ao renovar o token após %d tentativas", retry_count + 1)
                    return None

            # Tratamento de rate limit
            if resp.status_code == 429:
                for attempt in range(1, MAX_RETRIES_429 + 1):
                    _sleep_retry_after(resp, attempt)
                    try:
                        resp = requests.request(method, url, timeout=HTTP_TIMEOUT, headers=_auth_headers(), **kwargs)
                        if resp.status_code != 429:
                            return resp
                    except requests.RequestException as e:
                        logger.error("Erro de rede durante retentativa 429: %s", e)
                        return None

            # Outros erros HTTP
            logger.error(
                "Erro na requisição %s %s: HTTP %d - %s",
                method, url, resp.status_code, resp.text[:300]
            )
            return None

        except requests.RequestException as e:
            logger.error("Erro de rede na chamada %s %s: %s", method, url, e)
            return None

    logger.error("Número máximo de tentativas de renovação do token atingido")
    return None

def buscar_produtos(pagina: int = 1, limite: int = 100) -> list[dict]:
    url = f"{API_BASE_URL}/produtos?pagina={pagina}&limite={limite}"
    resp = _request_with_refresh("GET", url)
    if resp is None or resp.status_code != 200:
        if resp is not None:
            logger.error("Erro ao buscar produtos (HTTP %s): %s", resp.status_code, resp.text[:400])
        return []
    try:
        data = resp.json()
    except ValueError:
        logger.error("Resposta /produtos não é JSON.")
        return []
    produtos = data.get("data") or []
    # Em WARNING por padrão não polui; suba pra INFO se quiser ver páginas
    logger.info("Página %s: %s produtos", pagina, len(produtos))
    return produtos

def buscar_detalhe_produto(id_bling: int) -> dict | None:
    url = f"{API_BASE_URL}/produtos/{id_bling}"
    resp = _request_with_refresh("GET", url)
    if resp is None:
        return None
    if resp.status_code != 200:
        logger.warning("Detalhe produto %s retornou HTTP %s", id_bling, resp.status_code)
        return None
    try:
        data = resp.json()
    except ValueError:
        logger.error("Resposta /produtos/{id} não é JSON.")
        return None
    return data.get("data") or None
