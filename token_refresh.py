import requests
import os
from dotenv import load_dotenv
from logger import logger

ENV_PATH = ".env"
load_dotenv(dotenv_path=ENV_PATH)

def renovar_token():
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": os.getenv("BLING_REFRESH_TOKEN"),
        "client_id": os.getenv("BLING_CLIENT_ID"),
        "client_secret": os.getenv("BLING_CLIENT_SECRET"),
    }

    try:
        response = requests.post(url, data=payload, timeout=30)
    except requests.RequestException as e:
        logger.error("Network error while refreshing token: %s", str(e))
        return None

    if response.status_code == 200:
        try:
            tokens = response.json()
        except ValueError:
            logger.error("Token refresh returned non JSON")
            return None

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if not access_token or not refresh_token:
            logger.error("Token refresh response missing fields")
            return None

        atualizar_env("BLING_ACCESS_TOKEN", access_token)
        atualizar_env("BLING_REFRESH_TOKEN", refresh_token)

        logger.info("Tokens updated successfully")
        return access_token
    else:
        logger.error("Token refresh failed. Status: %s Body: %s", response.status_code, response.text[:500])
        return None

def atualizar_env(chave, novo_valor):
    linhas = []
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        linhas = []

    chave_existente = False
    for i, linha in enumerate(linhas):
        if linha.startswith(f"{chave}="):
            linhas[i] = f"{chave}={novo_valor}\n"
            chave_existente = True
            break

    if not chave_existente:
        linhas.append(f"{chave}={novo_valor}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(linhas)
