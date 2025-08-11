from logger import logger
import requests
import os
from dotenv import load_dotenv
from token_refresh import renovar_token

load_dotenv()

def get_token():
    return os.getenv("BLING_ACCESS_TOKEN")

def buscar_produtos(pagina=1):
    token = get_token()
    url = "https://www.bling.com.br/Api/v3/produtos"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    params = {
        "limit": 100,
        "pagina": pagina,
    }

    logger.info("Request products page=%s", pagina)
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
    except requests.RequestException as e:
        logger.error("Network error while calling products API: %s", str(e))
        return []

    if response.status_code == 401:
        logger.warning("Token expired. Attempting refresh")
        novo_token = renovar_token()
        if not novo_token:
            logger.error("Token refresh failed")
            return []
        headers["Authorization"] = f"Bearer {novo_token}"
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
        except requests.RequestException as e:
            logger.error("Network error after token refresh: %s", str(e))
            return []

    logger.info("Products API status code: %s", response.status_code)
    if response.status_code == 200:
        try:
            json_data = response.json()
        except ValueError:
            logger.error("Products API returned non JSON")
            return []
        produtos = json_data.get("data", [])
        logger.info("Products returned: %s", len(produtos))
        if produtos:
            primeiro_nome = produtos[0].get("nome")
            if primeiro_nome:
                logger.info("First product name: %s", primeiro_nome)
        return produtos
    else:
        logger.error("Products API error. Body: %s", response.text[:500])
        return []
