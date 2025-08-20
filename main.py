from logger import logger
import os
import db
from bling_api import buscar_produtos
from detalhes_bling import update_product_details

# Quantas horas até considerar "stale" e buscar detalhes novamente
DETAILS_MAX_AGE_HOURS = int(os.getenv("DETAILS_MAX_AGE_HOURS", "168"))  # 7 dias
BUSCA_LIMITE = int(os.getenv("BUSCA_LIMITE", "100"))  # itens por página

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
    dimensoes = p.get("dimensoes") or {}
    pesos = p.get("pesos") or {}
    categoria = p.get("categoria", {})
    id_categoria = None
    
    # Tenta extrair o ID da categoria de diferentes estruturas possíveis
    if isinstance(categoria, dict):
        id_categoria = categoria.get("id")
    elif isinstance(categoria, list) and len(categoria) > 0:
        id_categoria = categoria[0].get("id")
    
    return {
        "id_bling": int(p.get("id") or p.get("idBling") or 0),
        "codigo": p.get("codigo"),
        "nome": p.get("nome"),
        "preco": _safe_float(p.get("preco") or p.get("precoBase") or p.get("precoVenda")),
        "estoque": _safe_int(p.get("estoque") or p.get("estoqueAtual") or 0),
        "tipo": p.get("tipo"),
        "situacao": (p.get("situacao") or p.get("status") or "")[:1],
        "formato": p.get("formato"),
        "largura": _safe_float(dimensoes.get("largura") or dimensoes.get("larguraCm") or p.get("largura")),
        "altura": _safe_float(dimensoes.get("altura") or dimensoes.get("alturaCm") or p.get("altura")),
        "profundidade": _safe_float(dimensoes.get("profundidade") or dimensoes.get("comprimento") or p.get("profundidade")),
        "peso_liquido": _safe_float(pesos.get("liquido") or pesos.get("pesoLiquido") or p.get("peso_liquido")),
        "peso_bruto": _safe_float(pesos.get("bruto") or pesos.get("pesoBruto") or p.get("peso_bruto")),
        "id_categoria": _safe_int(id_categoria),
    }

def main():
    try:
        logger.warning("Iniciando sincronização com Bling...")  # aparece mesmo com LOG_LEVEL=WARNING
        conn = db.conectar_mysql()
        cursor = conn.cursor()

        total_processados = 0
        total_upserts = 0
        total_det_ok = 0
        total_det_skip = 0
        total_det_fail = 0

        pagina = 1
        while True:
            produtos_api = buscar_produtos(pagina=pagina, limite=BUSCA_LIMITE)
            if not produtos_api:
                break

            # Mapeia e faz upsert em lote
            mapeados = [_mapear_produto(p) for p in produtos_api if (p.get("id") or p.get("idBling"))]
            total_processados += len(mapeados)

            afetados = db.upsert_batch(cursor, mapeados)
            conn.commit()
            total_upserts += afetados

            # Detalhes somente quando necessário
            for mp in mapeados:
                ib = mp["id_bling"]
                try:
                    if db.needs_details(cursor, ib, DETAILS_MAX_AGE_HOURS):
                        ok = update_product_details(cursor, ib)
                        if ok:
                            total_det_ok += 1
                        else:
                            total_det_fail += 1
                    else:
                        total_det_skip += 1
                except Exception:
                    total_det_fail += 1

            conn.commit()  # commit após detalhes da página

            pagina += 1

        logger.warning(
            "Finalizado. Processados=%s | Upserts=%s | Detalhes ok=%s | Detalhes pulados=%s | Detalhes falha=%s",
            total_processados, total_upserts, total_det_ok, total_det_skip, total_det_fail
        )
        cursor.close()
        conn.close()

    except Exception:
        logger.exception("Erro fatal durante a execução")

if __name__ == "__main__":
    main()
