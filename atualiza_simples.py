import requests
import json
import mysql.connector
import time

DB_CONFIG = {
    'host': '108.167.132.218',
    'user': 'acdcco13_ti',
    'password': '*Spark1010',
    'database': 'acdcco13_banquinho'
}

ARQUIVO_JSON = 'produtos_bling_api.json'

def buscar_access_token():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuracoes_api WHERE chave = 'bling_access_token' LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row and row[0]:
        return row[0].strip()
    else:
        raise Exception("Access Token não encontrado no banco.")

def coletar_produtos_bling():
    access_token = buscar_access_token()
    produtos = []
    pagina = 1
    print("Iniciando coleta dos produtos do Bling...")

    while True:
        url = f"https://api.bling.com.br/Api/v3/produtos?pagina={pagina}&limite=100&tipo=P&situacao=A"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Erro ao consultar produtos (página {pagina}): {response.status_code} - {response.text}")
            break

        data = response.json()
        itens = data.get('data', [])
        if not itens:
            break

        produtos.extend([
            {
                "id": prod.get("id"),
                "codigo": prod.get("codigo"),
                "nome": prod.get("nome"),
                "preco": prod.get("preco", 0),
                "estoque": prod.get("estoque", {}).get("saldoVirtualTotal", 0)
            }
            for prod in itens
        ])
        print(f"Página {pagina}: {len(itens)} produtos coletados. Total até agora: {len(produtos)}")
        if len(itens) < 100:
            break
        pagina += 1

        # Delay de 1 segundo por página
        time.sleep(1)

    with open(ARQUIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    print(f"\nTotal encontrado na API: {len(produtos)} produtos.")
    print(f"Coletados e salvos em '{ARQUIVO_JSON}'.\n")
    return produtos

def atualizar_banco(produtos):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    atualizados = 0
    total = len(produtos)

    print(f"Iniciando atualização no banco. Total a processar: {total}")

    for idx, prod in enumerate(produtos, start=1):
        cursor.execute("""
            UPDATE produtos_bling
            SET nome = %s, preco = %s, estoque = %s
            WHERE id_bling = %s
        """, (prod['nome'], prod['preco'], prod['estoque'], prod['id']))
        if cursor.rowcount > 0:
            atualizados += 1
        print(f"[{idx}/{total}] {'Atualizado' if cursor.rowcount > 0 else 'Não encontrado'} | id_bling: {prod['id']} | codigo: {prod['codigo']}", end='\r')

    conn.commit()
    cursor.close()
    conn.close()
    print()  # Nova linha depois do loop
    print(f"\nTotal de produtos recebidos: {total}")
    print(f"Total realmente atualizados no banco: {atualizados}")
    print(f"Total não encontrados no banco: {total - atualizados}")

def main():
    produtos = coletar_produtos_bling()  # Coleta e salva o JSON
    atualizar_banco(produtos)            # Atualiza banco de dados

if __name__ == "__main__":
    main()
