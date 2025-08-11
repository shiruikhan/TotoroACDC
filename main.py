from logger import logger
import time
import os
import db
from bling_api import buscar_produtos
from detalhes_bling import update_product_details, FILA_RETRY

DETALHE_GAP = float(os.getenv("DETAILS_DELAY", "0.3"))
RETRY_FINAL_DELAY = 2.0

def _safe_float(value):
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

def _safe_int(value):
    try:
        return int(float(str(value).replace(",", ".")))
    except (ValueError, TypeError):
        return 0

def _mapear_produto(p: dict) -> dict:
    return {
        "id_bling": int(p.get("id") or p.get("idBling") or 0),
        "codigo": p.get("codigo"),
        "nome": p.get("nome"),
        "preco": _safe_float(p.get("preco") or p.get("precoBase") or p.get("precoVenda")),
        "estoque": _safe_int(p.get("estoque") or p.get("estoqueAtual") or 0),
        "tipo": p.get("tipo"),
        "situacao": (p.get("situacao") or p.get("status") or "")[:1],
        "formato": p.get("formato"),
    }

def main():
    try:
        logger.info("Iniciando sincronização com Bling...")
        conn = db.conectar_mysql()
        cursor = conn.cursor()

        total_processados = 0
        total_upserts = 0

        pagina = 1
        while True:
            produtos_api = buscar_produtos(pagina=pagina, limite=100)
            if not produtos_api:
                break

            for p in produtos_api:
                mp = _mapear_produto(p)
                if not mp["id_bling"]:
                    continue

                if db.inserir_ou_atualizar(cursor, mp):
                    total_upserts += 1
                    update_product_details(cursor, mp["id_bling"])
                    time.sleep(DETALHE_GAP)
                total_processados += 1

            logger.info("Página %s processada. Upserts acumulados: %s", pagina, total_upserts)
            pagina += 1
            time.sleep(0.5)

        if FILA_RETRY:
            logger.warning("Reprocessando detalhes pendentes: %s itens", len(FILA_RETRY))
            for id_bling in list(FILA_RETRY):
                time.sleep(RETRY_FINAL_DELAY)
                if update_product_details(cursor, id_bling):
                    FILA_RETRY.discard(id_bling)

        logger.info(
            "Finalizado. Processados: %s | Inseridos/Atualizados: %s | Pendentes detalhe: %s",
            total_processados, total_upserts, len(FILA_RETRY)
        )
        cursor.close()
        conn.close()

    except Exception:
        logger.exception("Erro fatal durante a execução")

if __name__ == "__main__":
    main()
