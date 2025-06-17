import time
from bling_api import buscar_produtos
from db import conectar_mysql, criar_tabela, inserir_ou_atualizar

def main():
    try:
        print("🚀 Iniciando sincronização com o Bling")

        print("🔌 Conectando ao banco de dados...")
        conn = conectar_mysql()
        cursor = conn.cursor()

        print("📦 Criando tabela (caso não exista)...")
        criar_tabela(cursor)

        offset = 0
        limite = 100
        total_inseridos = 0

        while True:
            print(f"➡️ Buscando produtos | Offset: {offset}")
            produtos = buscar_produtos(offset)
            print(f"🔍 Produtos retornados: {len(produtos)}")

            if not produtos:
                print("⚠️ Nenhum produto retornado. Encerrando.")
                break

            for p in produtos:
                produto_data = {
                    "id": int(p["id"]),
                    "codigo": p.get("codigo"),
                    "nome": p.get("nome"),
                    "preco": float(p.get("preco", 0)),
                    "saldovirtualtotal": float(p.get("estoque", {}).get("saldoVirtualTotal", 0)),
                }
                inserir_ou_atualizar(cursor, produto_data)
                total_inseridos += 1

            print("✅ Commitando alterações...")
            conn.commit()

            offset += limite
            time.sleep(0.5)

        print(f"🏁 Sincronização concluída com {total_inseridos} produtos inseridos/atualizados.")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Erro fatal na execução: {e}")

if __name__ == "__main__":
    print("📄 Executando main.py diretamente")
    main()
