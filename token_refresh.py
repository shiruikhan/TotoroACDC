import os
import requests
from dotenv import load_dotenv
from logger import logger

ENV_PATH = os.getenv("ENV_PATH", ".env")
load_dotenv(dotenv_path=ENV_PATH)

TOKEN_URL = "https://www.bling.com.br/Api/v3/oauth/token"

def _update_env_var(key: str, value: str) -> None:
    os.environ[key] = value or ""
    try:
        try:
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}\n")
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        logger.warning("Falha ao persistir %s no .env: %s", key, e)

def renovar_token() -> str | None:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": os.getenv("BLING_REFRESH_TOKEN"),
        "client_id": os.getenv("BLING_CLIENT_ID"),
        "client_secret": os.getenv("BLING_CLIENT_SECRET"),
    }
    try:
        resp = requests.post(TOKEN_URL, data=payload, timeout=30)
    except requests.RequestException as e:
        logger.error("Erro de rede ao renovar token: %s", e)
        return None

    if resp.status_code != 200:
        logger.error("Falha ao renovar token: HTTP %s - %s", resp.status_code, resp.text[:300])
        return None

    try:
        data = resp.json()
    except ValueError:
        logger.error("Resposta de renovação de token não é JSON.")
        return None

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        logger.error("Resposta de token sem access_token.")
        return None

    _update_env_var("BLING_ACCESS_TOKEN", access_token)
    if refresh_token:
        _update_env_var("BLING_REFRESH_TOKEN", refresh_token)

    logger.info("Token do Bling renovado com sucesso.")
    return access_token
