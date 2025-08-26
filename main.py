"""Sincroniza produtos do Bling com o banco de dados MySQL."""
from logger import logger
import os
import db
from bling_api import buscar_produtos
from detalhes_bling import update_product_details

DETAILS_MAX_AGE_HOURS = int(os.getenv("DETAILS_MAX_AGE_HOURS", "168"))

def _safe_float(value):
    """Converte um valor para float de forma segura.
    
    Args:
        value: Valor a ser convertido para float
    
    Returns:
        float: Valor convertido ou 0.0 em caso de erro
    """
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))  # Converte vírgula para ponto
    except (ValueError, TypeError):
        return 0.0

def _mapear_produto(p: dict) -> dict:
    """Mapeia os dados do produto da API do Bling para o formato do banco de dados.
    
    Args:
        p (dict): Dicionário com dados do produto da API
    
    Returns:
        dict: Dicionário com dados mapeados para o formato do banco
    """
    # Extrai dados de estoque
    estoque = 0
    if 'estoques' in p and p['estoques']:
        for deposito in p['estoques']:
            estoque += _safe_float(deposito.get('saldoVirtualTotal', 0))
    
    # Extrai dimensões
    dimensoes = p.get('dimensoes', {})
    
    # Extrai dados de preço
    preco = 0
    if isinstance(p.get('preco'), dict):
        preco = _safe_float(p['preco'].get('preco', 0))
    else:
        preco = _safe_float(p.get('preco', 0))
    
    # Mapeia os campos do produto para o formato do banco
    return {
        "id_bling": int(p.get("id")),
        "codigo": p.get("codigo"),
        "nome": p.get("nome"),
        "preco": p.get("preco", 0),
        "estoque": (p.get("estoque") or {}).get("saldoVirtualTotal", 0),
        "tipo": p.get("tipo"),
        "situacao": (p.get("situacao") or "")[:1],
        "formato": p.get("formato"),
        "largura": _safe_float(dimensoes.get("largura")),
        "altura": _safe_float(dimensoes.get("altura")),
        "profundidade": _safe_float(dimensoes.get("profundidade")),
        "peso_liquido": p.get("pesoLiquido"),
        "peso_bruto": p.get("pesoBruto")
    }

def main():
    """Função principal do script de sincronização.
    
    Realiza a sincronização dos produtos do Bling com o banco de dados local,
    incluindo seus detalhes e informações complementares.
    """
    conn = None
    try:
        logger.info("Iniciando sincronização com Bling...")
        
        # Estabelece conexão com o banco de dados
        conn = db.conectar_mysql()
        conn.autocommit = False  # Desativa autocommit para melhor controle
        cursor = conn.cursor()

        total_processados = 0
        total_upserts = 0
        total_det_ok = 0
        total_det_skip = 0
        total_det_fail = 0

        # Busca paginada de todos os produtos da API
        todos_produtos = []
        pagina = 1
        while True:
            produtos_api = buscar_produtos(pagina=pagina)
            if not produtos_api:
                break
            todos_produtos.extend(produtos_api)
            pagina += 1

        logger.info("Total de produtos encontrados na API: %s", len(todos_produtos))

        # Processa todos os produtos em um único lote
        mapeados = [_mapear_produto(p) for p in todos_produtos if p.get("id")]
        total_processados = len(mapeados)

        # Faz um único upsert em lote
        if mapeados:
            total_upserts = db.upsert_batch(cursor, mapeados)
            conn.commit()
            
            # Verifica se os registros foram inseridos
            cursor.execute("SELECT COUNT(*) FROM produtos_bling")
            total_registros = cursor.fetchone()[0]
            logger.info("Total de registros no banco após upsert: %s", total_registros)

        # Processa detalhes em lote
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
                conn.rollback()  # Rollback em caso de erro

            # Commit a cada 100 detalhes processados
            if (total_det_ok + total_det_skip + total_det_fail) % 100 == 0:
                conn.commit()
                logger.info(
                    "Commit realizado após processar %s detalhes",
                    total_det_ok + total_det_skip + total_det_fail,
                )

        conn.commit()  # commit final
        
        # Verifica total final de registros
        cursor.execute("SELECT COUNT(*) FROM produtos_bling")
        total_final = cursor.fetchone()[0]
        logger.info("Total final de registros no banco: %s", total_final)

        logger.info(
            "Finalizado. Processados=%s | Upserts=%s | Detalhes ok=%s | Detalhes pulados=%s | Detalhes falha=%s",
            total_processados, total_upserts, total_det_ok, total_det_skip, total_det_fail
        )
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Erro fatal durante a execução")
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
