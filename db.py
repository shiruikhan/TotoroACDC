import os
from typing import Any
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
    conn.autocommit = True
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

def inserir_ou_atualizar(cursor, produto: dict) -> bool:
    try:
        sql = """
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
        params = (
            int(produto["id_bling"]),
            produto.get("codigo"),
            (produto.get("nome") or "")[:255],
            _to_float(produto.get("preco")),
            _to_int(produto.get("estoque")),
            produto.get("tipo"),
            (produto.get("situacao") or "")[:1],
            produto.get("formato"),
        )
        cursor.execute(sql, params)
        return True
    except Exception as e:
        logger.error("Falha ao inserir/atualizar id_bling=%s: %s", produto.get("id_bling"), e)
        return False
