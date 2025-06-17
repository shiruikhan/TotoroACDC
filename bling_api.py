import requests
import os
from dotenv import load_dotenv
from token_refresh import renovar_token

load_dotenv()

def get_token():
    return os.getenv("BLING_ACCESS_TOKEN")

def buscar_produtos(offset=0):
    token = get_token()
    url = "https://www.bling.com.br/Api/v3/produtos"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    params = {
        "limit": 100,
        "offset": offset,
        "filters": "tipo[P];situacao[A]",
        "filtroSaldoEstoque": 1
    }

    print(f"📡 Requisição -> offset={offset}")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 401:
        print("⚠️ Token expirado. Tentando renovar...")
        novo_token = renovar_token()
        if not novo_token:
            raise Exception("Não foi possível renovar o token.")
        headers["Authorization"] = f"Bearer {novo_token}"
        response = requests.get(url, headers=headers, params=params)

    print(f"📥 Status code: {response.status_code}")
    if response.status_code == 200:
        json_data = response.json()
        produtos = json_data.get("data", [])
        print(f"🔍 Produtos retornados: {len(produtos)}")
        if produtos:
            print(f"→ Primeiro produto: {produtos[0].get('nome')}")
        return produtos
    else:
        print("❌ Erro na resposta da API:")
        print(response.text)
        return []
