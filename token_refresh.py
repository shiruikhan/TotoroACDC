import requests
import os
from dotenv import load_dotenv
from logger import logger


ENV_PATH = '.env'
load_dotenv(dotenv_path=ENV_PATH)

def renovar_token():
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": os.getenv("BLING_REFRESH_TOKEN"),
        "client_id": os.getenv("BLING_CLIENT_ID"),
        "client_secret": os.getenv("BLING_CLIENT_SECRET")
    }

    response = requests.post(url, data=payload)
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        atualizar_env("BLING_ACCESS_TOKEN", access_token)
        atualizar_env("BLING_REFRESH_TOKEN", refresh_token)

        logger.info("Tokens atualizados com sucesso.")
        return access_token
    else:
        logger.error("Erro ao renovar token: %s", response.status_code)
        logger.info(response.text)
        return None

def atualizar_env(chave, novo_valor):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        linhas = f.readlines()

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