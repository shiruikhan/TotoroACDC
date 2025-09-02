import os
import requests
import mysql.connector
from dotenv import load_dotenv
from logger import logger

# Carregar variáveis de ambiente
ENV_PATH = os.getenv("ENV_PATH", ".env")
load_dotenv(dotenv_path=ENV_PATH)

def _update_env_var(key: str, value: str) -> None:
    """Atualiza uma variável no processo e persiste no arquivo .env.

    Em caso de falha de persistência, mantém o valor no ambiente e registra um aviso.
    """
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

# Configuração do banco de dados usando variáveis de ambiente
DB_CONFIG = {
    'host': '108.167.132.218',
    'user': 'acdcco13_ti',
    'password': '*Spark1010',
    'database': 'acdcco13_banquinho'
}

def atualizar_tokens_bling():
    try:
        # Obter credenciais do .env
        refresh_token = os.getenv('BLING_REFRESH_TOKEN')
        client_id = os.getenv('BLING_CLIENT_ID')
        client_secret = os.getenv('BLING_CLIENT_SECRET')
        
        if not all([refresh_token, client_id, client_secret]):
            logger.error("Credenciais incompletas para renovação do token. Verifique BLING_REFRESH_TOKEN, BLING_CLIENT_ID e BLING_CLIENT_SECRET no .env")
            print("[ERRO] Credenciais incompletas no arquivo .env")
            return

        # Conectar ao banco
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Fazer requisição para obter novos tokens
        url = 'https://www.bling.com.br/Api/v3/oauth/token'
        auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, data=payload, auth=auth, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        new_access_token = data.get('access_token')
        new_refresh_token = data.get('refresh_token')
        
        if not new_access_token:
            logger.error("Resposta de token sem access_token.")
            print("[ERRO] Resposta da API sem access_token")
            return

        # Atualizar access_token no banco
        cursor.execute("UPDATE configuracoes_api SET valor = %s WHERE chave = 'totoro_access_token'", (new_access_token,))
        # Atualizar refresh_token no banco se fornecido
        if new_refresh_token:
            cursor.execute("UPDATE configuracoes_api SET valor = %s WHERE chave = 'totoro_refresh_token'", (new_refresh_token,))
            logger.info("Refresh token atualizado no banco.")
        
        conn.commit()
        
        # Atualizar tokens no arquivo .env para futuros refreshs
        _update_env_var("BLING_ACCESS_TOKEN", new_access_token)
        if new_refresh_token:
            _update_env_var("BLING_REFRESH_TOKEN", new_refresh_token)
            logger.info("Refresh token atualizado no .env.")
        
        logger.info("Token do Bling renovado com sucesso.")
        print("[SUCESSO] Access Token e Refresh Token atualizados com sucesso no banco e .env.")

    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", "?")
        body = getattr(e.response, "text", "")
        logger.error("Erro HTTP ao renovar token: %s - %s", status, body[:300])
        if status == 400:
            logger.error("Possível refresh token inválido ou expirado. Necessário reautenticar.")
        print(f"[ERRO] Erro HTTP ao renovar token: {status}")
    except requests.RequestException as e:
        logger.error("Erro de rede ao renovar token: %s", e)
        print(f"[ERRO] Erro de rede: {str(e)}")
    except ValueError as e:
        logger.error("Resposta de renovação de token não é JSON: %s", e)
        print("[ERRO] Resposta inválida da API")
    except Exception as e:
        logger.error("Falha ao atualizar tokens: %s", str(e))
        print(f"[ERRO] Falha ao atualizar tokens: {str(e)}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


# Executar
atualizar_tokens_bling()
