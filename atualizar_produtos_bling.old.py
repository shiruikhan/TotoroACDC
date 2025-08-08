import requests
import mysql.connector
import json
import time
from datetime import datetime

# --- CONFIGURAÇÃO DO BANCO ---
DB_CONFIG = {
    'host': '108.167.132.218',
    'user': 'acdcco13_ti',
    'password': '*Spark1010',
    'database': 'acdcco13_banquinho'
}

JSON_PATH = 'produtos_bling.json'
FALHAS_PATH = 'falhas_bling.json'

MAX_RETRY = 3
DELAY_OK = 1.0    # intervalo entre requisições bem-sucedidas
DELAY_FAIL = 5.0  # intervalo após falha

def buscar_access_token():
    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT valor FROM configuracoes_api WHERE chave = 'bling_access_token'")
            row = cursor.fetchone()
            if row and row[0]:
                return row[0].strip()
            else:
                raise Exception("Access Token não encontrado no banco.")

def buscar_ids_produtos(headers):
    ids = []
    pagina = 1
    while True:
        url = f"https://api.bling.com.br/Api/v3/produtos?pagina={pagina}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                print(f"❌ Erro página {pagina}: {resp.status_code} - {resp.text}")
                break

            data = resp.json().get('data', [])
            if not data:
                break

            for item in data:
                if item.get('tipo') == 'P' and item.get('formato') == 'S':
                    ids.append(item.get('id'))

            if len(data) < 100:
                break
            pagina += 1
            time.sleep(DELAY_OK)
        except Exception as e:
            print(f"❌ Falha ao buscar IDs na página {pagina}: {e}")
            break
    return ids

def buscar_detalhes_produto(produto_id, headers):
    url = f"https://api.bling.com.br/Api/v3/produtos/{produto_id}"
    for tentativa in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                if data.get('tipo') != 'P' or data.get('formato') != 'S':
                    return None
                return {
                    'codigo': data.get('codigo', ''),
                    'nome': data.get('nome', ''),
                    'preco': data.get('preco', 0),
                    'estoque': data.get('estoque', {}).get('saldoVirtualTotal', 0),
                    'largura': data.get('dimensoes', {}).get('largura'),
                    'altura': data.get('dimensoes', {}).get('altura'),
                    'profundidade': data.get('dimensoes', {}).get('profundidade'),
                    'peso_liquido': data.get('pesoLiquido'),
                    'peso_bruto': data.get('pesoBruto'),
                    'imagem': (
                        data.get('midia', {}).get('imagens', {}).get('internas', [{}])[0].get('link')
                        if data.get('midia', {}).get('imagens', {}).get('internas') else 'img/imagem_indisponivel.png'
                    ) or 'img/imagem_indisponivel.png',
                    'situacao': data.get('situacao', 'A')
                }
            elif resp.status_code == 504:
                print(f"⚠️ 504 Gateway Timeout ao buscar produto {produto_id}, tentativa {tentativa}/{MAX_RETRY}")
            else:
                print(f"❌ Erro {resp.status_code} ao buscar produto {produto_id}: {resp.text}")
                break
        except Exception as e:
            print(f"❌ Exception ao buscar produto {produto_id}: {e}")
        time.sleep(DELAY_FAIL)
    return None

def gerar_json_produtos(headers):
    print("📦 Buscando IDs dos produtos tipo P e formato S...")
    ids = buscar_ids_produtos(headers)
    print(f"🔢 Total de produtos filtrados: {len(ids)}")

    produtos = []
    falhas = []
    for i, pid in enumerate(ids, 1):
        print(f"[{i}/{len(ids)}] Coletando produto ID {pid}")
        produto = buscar_detalhes_produto(pid, headers)
        if produto:
            produtos.append(produto)
        else:
            falhas.append(pid)
        time.sleep(DELAY_OK)

    # Segunda tentativa para falhas
    if falhas:
        print(f"\n🔁 Tentando novamente {len(falhas)} produtos que falharam...")
        segunda_falha = []
        for pid in falhas:
            print(f"[Retry] Coletando produto ID {pid}")
            produto = buscar_detalhes_produto(pid, headers)
            if produto:
                produtos.append(produto)
            else:
                segunda_falha.append(pid)
            time.sleep(DELAY_OK)
        falhas = segunda_falha

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(produtos, f, ensure_ascii=False, indent=2)
    print(f"📁 JSON salvo como: {JSON_PATH}")

    if falhas:
        with open(FALHAS_PATH, 'w', encoding='utf-8') as f:
            json.dump(falhas, f, ensure_ascii=False, indent=2)
        print(f"⚠️ Falhas persistentes: {len(falhas)} produtos. IDs salvos em {FALHAS_PATH}")

def importar_para_banco():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        produtos = json.load(f)

    with mysql.connector.connect(**DB_CONFIG) as conn:
        with conn.cursor(dictionary=True) as cursor:
            total_inseridos = 0
            total_atualizados = 0
            total_iguais = 0
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            for produto in produtos:
                cursor.execute("SELECT * FROM produtos_bling WHERE codigo = %s", (produto['codigo'],))
                row = cursor.fetchone()

                campos = ['nome', 'preco', 'estoque', 'largura', 'altura', 'profundidade',
                          'peso_liquido', 'peso_bruto', 'imagem', 'situacao']

                valores_novos = [produto.get(c) for c in campos]

                if row:
                    alterado = any(str(row.get(campo)) != str(produto.get(campo)) for campo in campos)
                    if alterado:
                        cursor.execute("""
                            UPDATE produtos_bling
                            SET nome = %s, preco = %s, estoque = %s, largura = %s, altura = %s,
                                profundidade = %s, peso_liquido = %s, peso_bruto = %s,
                                imagem = %s, situacao = %s, data_alteracao = %s
                            WHERE codigo = %s
                        """, valores_novos + [now, produto['codigo']])
                        total_atualizados += 1
                        print(f"🔄 Atualizado: {produto['codigo']}")
                    else:
                        total_iguais += 1
                        print(f"⏩ Inalterado: {produto['codigo']}")
                else:
                    cursor.execute("""
                        INSERT INTO produtos_bling (
                            codigo, nome, preco, estoque, largura, altura, profundidade,
                            peso_liquido, peso_bruto, imagem, situacao, data_alteracao
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [produto['codigo']] + valores_novos + [now])
                    total_inseridos += 1
                    print(f"✅ Inserido: {produto['codigo']}")

            conn.commit()

    print(f"\n🏁 Importação finalizada:")
    print(f"📥 Inseridos: {total_inseridos}")
    print(f"♻️ Atualizados: {total_atualizados}")
    print(f"🟰 Inalterados: {total_iguais}")

def executar():
    print("🔄 Iniciando processo completo...")
    try:
        access_token = buscar_access_token()
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        gerar_json_produtos(headers)
        importar_para_banco()
        print("✅ Processo concluído com sucesso.")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    executar()
