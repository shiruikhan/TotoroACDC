from logger import logger
import time
from bling_api import buscar_produtos
from db import conectar_mysql, criar_tabela, inserir_ou_atualizar

def main():
    try:
        logger.info("🚀 Iniciando sincronização com o Bling")

        logger.info("🔌 Conectando ao banco de dados...")
        conn = conectar_mysql()
        cursor = conn.cursor()

        logger.info("📦 Criando tabela (caso não exista)...")
        criar_tabela(cursor)

        pagina = 1
        total_inseridos = 0

        while True:
            logger.info(f"➡️ Buscando produtos | Página: {pagina}")
            produtos = buscar_produtos(pagina)
            logger.info(f"🔍 Produtos retornados: {len(produtos)}")

            if not produtos:
                logger.warning("⚠️ Nenhum produto retornado. Encerrando.")
                break

            for p in produtos:
                produto_data = {
                    "id": int(p["id"]),
                    "codigo": p.get("codigo"),
                    "nome": p.get("nome"),
                    "preco": float(p.get("preco", 0)),
                    "saldovirtualtotal": float(p.get("estoque", {}).get("saldoVirtualTotal", 0)),
                }
                inserido = inserir_ou_atualizar(cursor, produto_data, conn)
                if inserido:
                    total_inseridos += 1

            logger.info("✅ Commitando alterações...")
            conn.commit()

            pagina += 1
            time.sleep(0.5)

        logger.info(f"🏁 Sincronização concluída com {total_inseridos} produtos inseridos/atualizados.")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.critical(f"❌ Erro fatal na execução: {e}")

if __name__ == "__main__":
    logger.info("📄 Executando main.py diretamente")
    main()
