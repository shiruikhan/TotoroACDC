import requests
import mysql.connector

# Configuração do banco de dados
DB_CONFIG = {
    'host': '108.167.132.218',
    'user': 'acdcco13_ti',
    'password': '*Spark1010',
    'database': 'acdcco13_banquinho'
}

# String já codificada em base64 (igual à usada no PHP)
AUTH_BASE64 = 'ZDA5YWU3YjM4ZWIyNDFkZWNmYTUzZGRlMWVlMzU0ZTE3MDFkNmUwMzowOTRkODQ2ZGQyYTAzMWM5ZTkzZDFiMjBhZGU2MWM1Mzk3NjMzYWIxYjI0YTYzYTUxYTQxZTllMGU3M2U='

def atualizar_tokens_bling():
    try:
        # Conectar ao banco
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Buscar refresh_token
        cursor.execute("SELECT valor FROM configuracoes_api WHERE chave = 'bling_refresh_token' LIMIT 1")
        row = cursor.fetchone()
        if not row or not row['valor']:
            print("[ERRO] Refresh Token não encontrado no banco.")
            return

        refresh_token = row['valor']

        # Fazer requisição para obter novos tokens
        url = 'https://api.bling.com.br/Api/v3/oauth/token'
        headers = {
            'Authorization': f'Basic {AUTH_BASE64}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        response = requests.post(url, headers=headers, data=payload)
        data = response.json()

        if response.status_code == 200 and 'access_token' in data and 'refresh_token' in data:
            new_access_token = data['access_token']
            new_refresh_token = data['refresh_token']

            # Atualizar access_token
            cursor.execute("UPDATE configuracoes_api SET valor = %s WHERE chave = 'bling_access_token'", (new_access_token,))
            # Atualizar refresh_token
            cursor.execute("UPDATE configuracoes_api SET valor = %s WHERE chave = 'bling_refresh_token'", (new_refresh_token,))
            conn.commit()

            print("[SUCESSO] Access Token e Refresh Token atualizados com sucesso.")
        else:
            print("[ERRO] Erro na resposta da API Bling.")
            print(data)

    except Exception as e:
        print(f"[ERRO] Falha ao atualizar tokens: {str(e)}")

    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# Executar
atualizar_tokens_bling()
