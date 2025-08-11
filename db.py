import os
from typing import Any, Iterable, List, Tuple
import mysql.connector
from dotenv import load_dotenv
from logger import logger

load_dotenv()

def conectar_mysql():
    cfg = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "use_pure": True,
        "connection_timeout": 10,
    }
    faltando = [k for k in ("host","user","password","database") if not cfg[k]]
    if faltando:
        raise RuntimeError(f"Variáveis de ambiente ausentes: {', '.join(faltando)}")
    conn = mysql.connector.connect(**cfg)
    # Melhora desempenho em lote:
    conn.autocommit = False
    logger.info("Conectado ao banco %s:%s/%s", cfg["host"], cfg["port"], cfg["database"])
    return conn

def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

def _to_int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (ValueError, TypeError):
        return 0

_SQL_UPSERT = """
INSERT INTO temp_produtos_bling
    (id_bling, codigo, nome, preco, estoque, tipo, situacao, formato)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    codigo   = VALUES(codigo),
    nome     = VALUES(nome),
    preco    = VALUES(preco),
    estoque  = VALUES(estoque),
    tipo     = VALUES(tipo),
    situacao = VALUES(situacao),
    formato  = VALUES(formato)
"""

def _params_upsert(produto: dict) -> Tuple:
    return (
        int(produto["id_bling"]),
        produto.get("codigo"),
        (produto.get("nome") or "")[:255],
        _to_float(produto.get("preco")),
        _to_int(produto.get("estoque")),
        produto.get("tipo"),
        (produto.get("situacao") or "")[:1],
        produto.get("formato"),
    )

def inserir_ou_atualizar(cursor, produto: dict) -> bool:
    """Mantido para compatibilidade; usa a mesma SQL do batch."""
    try:
        cursor.execute(_SQL_UPSERT, _params_upsert(produto))
        return True
    except Exception as e:
        logger.error("Falha ao inserir/atualizar id_bling=%s: %s", produto.get("id_bling"), e)
        return False

def upsert_batch(cursor, produtos: Iterable[dict]) -> int:
    """Upsert em lote via executemany + commit explícito (melhor throughput)."""
    itens = [p for p in produtos if p.get("id_bling")]
    if not itens:
        return 0
    params: List[Tuple] = [_params_upsert(p) for p in itens]
    cursor.executemany(_SQL_UPSERT, params)
    return len(params)

def needs_details(cursor, id_bling: int, max_age_hours: int) -> bool:
    """
    Retorna True se deve buscar detalhes:
    - imagem nula/vazia, OU
    - data_alteracao nula, OU
    - data_alteracao mais antiga que NOW() - max_age_hours.
    """
    cursor.execute(
        """
        SELECT
            (imagem IS NULL OR imagem = '') AS img_vazia,
            (data_alteracao IS NULL OR data_alteracao < (NOW() - INTERVAL %s HOUR)) AS stale
        FROM temp_produtos_bling
        WHERE id_bling = %s
        """,
        (int(max_age_hours), int(id_bling))
    )
    row = cursor.fetchone()
    if row is None:
        # Se não achar, tratar como precisa (segurança)
        return True
    img_vazia, stale = row
    return bool(img_vazia or stale)
