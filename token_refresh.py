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
    # Verificar se temos todas as credenciais necessárias
    refresh_token = os.getenv("BLING_REFRESH_TOKEN")
    client_id = os.getenv("BLING_CLIENT_ID")
    client_secret = os.getenv("BLING_CLIENT_SECRET")

    if not all([refresh_token, client_id, client_secret]):
        logger.error("Credenciais incompletas para renovação do token. Verifique BLING_REFRESH_TOKEN, BLING_CLIENT_ID e BLING_CLIENT_SECRET no .env")
        return None

    # Autenticação Basic usando client_id e client_secret
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    try:
        resp = requests.post(
            TOKEN_URL,
            data=payload,
            auth=auth,
            timeout=30,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        resp.raise_for_status()  # Levanta exceção para status codes >= 400
    except requests.exceptions.HTTPError as e:
        logger.error("Erro HTTP ao renovar token: %s - %s", e.response.status_code, e.response.text[:300])
        if e.response.status_code == 400:
            logger.error("Possível refresh token inválido ou expirado. Necessário reautenticar.")
        return None
    except requests.RequestException as e:
        logger.error("Erro de rede ao renovar token: %s", e)
        return None

    try:
        data = resp.json()
    except ValueError:
        logger.error("Resposta de renovação de token não é JSON.")
        return None

    access_token = data.get("access_token")
    new_refresh_token = data.get("refresh_token")

    if not access_token:
        logger.error("Resposta de token sem access_token.")
        return None

    _update_env_var("BLING_ACCESS_TOKEN", access_token)
    if new_refresh_token:
        _update_env_var("BLING_REFRESH_TOKEN", new_refresh_token)
        logger.info("Refresh token atualizado com sucesso.")

    logger.info("Token do Bling renovado com sucesso.")
    return access_token
