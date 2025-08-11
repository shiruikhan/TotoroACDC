from logger import logger
import time
from bling_api import buscar_produtos
from db import conectar_mysql, criar_tabela, inserir_ou_atualizar

def _safe_float(value):
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

def main():
    try:
        logger.info("Starting synchronization with Bling")

        logger.info("Connecting to database")
        conn = conectar_mysql()
        cursor = conn.cursor()

        logger.info("Creating table if not exists")
        criar_tabela(cursor)

        pagina = 1
        total_inseridos = 0

        while True:
            logger.info("Fetching products page=%s", pagina)
            produtos = buscar_produtos(pagina)
            logger.info("Items received: %s", len(produtos))

            if not produtos:
                logger.warning("No products returned. Stopping")
                break

            for p in produtos:
                estoque_dict = p.get("estoque") or {}
                if not isinstance(estoque_dict, dict):
                    estoque_dict = {}
                produto_data = {
                    "id_bling": int(p.get("id")) if p.get("id") is not None else 0,
                    "codigo": p.get("codigo"),
                    "nome": p.get("nome"),
                    "preco": _safe_float(p.get("preco", 0)),
                    "estoque": _safe_float(estoque_dict.get("saldoVirtualTotal", 0)),
                    "tipo": p.get("tipo"),
                    "situacao": p.get("situacao"),
                    "formato": p.get("formato"),
                }
                inserido = inserir_ou_atualizar(cursor, produto_data, conn)
                if inserido:
                    total_inseridos += 1

            logger.info("Commit page results to database")
            conn.commit()

            pagina += 1
            time.sleep(0.5)

        logger.info("Synchronization finished. Total inserted or updated: %s", total_inseridos)

        cursor.close()
        conn.close()

    except Exception:
        logger.exception("Fatal error during execution")

if __name__ == "__main__":
    logger.info("Running main.py directly")
    main()
