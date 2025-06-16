import requests
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("BLING_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLING_CLIENT_SECRET")

def obter_token():
    url = "https://www.bling.com.br/Api/v3/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Erro ao obter token: {response.status_code}\n{response.text}")

def buscar_produtos(token, pagina=1):
    url = "https://www.bling.com.br/Api/v3/produtos"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "limit": 100,
        "offset": (pagina - 1) * 100,
        "filters": "tipo[P];situacao[A]"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        raise Exception(f"Erro ao buscar produtos: {response.status_code}\n{response.text}")
