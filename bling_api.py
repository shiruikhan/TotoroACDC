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
        "Accept": "application/json"
    }

    params = {
        "limit": 100,
        "pagina": pagina
    }

    logger.info(f"Requisição -> página={pagina}")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 401:
        logger.warning("Token expirado. Tentando renovar...")
        novo_token = renovar_token()
        if not novo_token:
            raise Exception("Não foi possível renovar o token.")
        headers["Authorization"] = f"Bearer {novo_token}"
        response = requests.get(url, headers=headers, params=params)

    logger.info(f"Status code: {response.status_code}")
    if response.status_code == 200:
        json_data = response.json()
        produtos = json_data.get("data", [])
        logger.info(f"Produtos retornados: {len(produtos)}")
        if produtos:
            logger.info(f"→ Primeiro produto: {produtos[0].get('nome')}")
        return produtos
    else:
        logger.error("Erro na resposta da API:")
        logger.error(response.text)
        return []
