"""Funções de acesso e escrita ao banco MySQL usadas pela sincronização.

Exige variáveis de ambiente:
- DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""
from __future__ import annotations

import os
from typing import Any, Iterable, List, Tuple

import mysql.connector
from dotenv import load_dotenv
from logger import logger

load_dotenv()


def conectar_mysql():
    """Abre conexão com MySQL usando variáveis de ambiente.

    Returns:
        mysql.connector.MySQLConnection: conexão ativa com autocommit desabilitado.

    Raises:
        RuntimeError: se variáveis obrigatórias estiverem ausentes.
    """
    cfg = {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
        "use_pure": True,
        "connection_timeout": 10,
    }
    faltando = [k for k in ("host", "user", "password", "database") if not cfg[k]]
    if faltando:
        raise RuntimeError(f"Variáveis de ambiente ausentes: {', '.join(faltando)}")

    conn = mysql.connector.connect(**cfg)
    conn.autocommit = False
    logger.info(
        "Conectado ao banco %s:%s/%s", cfg["host"], cfg["port"], cfg["database"]
    )
    return conn


def _to_float(value: Any) -> float:
    """Converte valor para float de forma tolerante a vírgulas e None."""
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def _to_int(value: Any) -> int:
    """Converte valor para int aceitando entradas com vírgula/ponto."""
    try:
        return int(float(str(value).replace(",", ".")))
    except (ValueError, TypeError):
        return 0


_SQL_UPSERT = (
    """
INSERT INTO produtos_bling
    (id_bling, codigo, nome, preco, estoque, tipo, situacao, formato,
     largura, altura, profundidade, peso_liquido, peso_bruto)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    id_bling     = VALUES(id_bling),
    codigo       = VALUES(codigo),
    nome         = VALUES(nome),
    preco        = VALUES(preco),
    estoque      = VALUES(estoque),
    tipo         = VALUES(tipo),
    situacao     = VALUES(situacao),
    formato      = VALUES(formato),
    largura      = VALUES(largura),
    altura       = VALUES(altura),
    profundidade = VALUES(profundidade),
    peso_liquido = VALUES(peso_liquido),
    peso_bruto   = VALUES(peso_bruto),
    data_alteracao = CURRENT_TIMESTAMP
"""
)


def _params_upsert(produto: dict) -> Tuple:
    """Prepara parâmetros para o upsert em produtos_bling."""
    return (
        int(produto["id_bling"]),
        produto.get("codigo"),
        (produto.get("nome") or "")[:255],
        _to_float(produto.get("preco")),
        _to_int(produto.get("estoque")),
        produto.get("tipo"),
        (produto.get("situacao") or "")[:1],
        produto.get("formato"),
        _to_float(produto.get("largura")),
        _to_float(produto.get("altura")),
        _to_float(produto.get("profundidade")),
        _to_float(produto.get("peso_liquido")),
        _to_float(produto.get("peso_bruto"))
    )


def inserir_ou_atualizar(cursor, produto: dict) -> bool:
    """Insere/atualiza um único produto. Preferir upsert_batch para lotes."""
    try:
        cursor.execute(_SQL_UPSERT, _params_upsert(produto))
        return True
    except Exception as e:
        logger.error(
            "Falha ao inserir/atualizar id_bling=%s: %s", produto.get("id_bling"), e
        )
        return False


def upsert_batch(cursor, produtos: Iterable[dict]) -> int:
    """Insere/atualiza múltiplos produtos em lote (executemany).

    O commit é responsabilidade do chamador.

    Returns:
        int: quantidade de itens enviados ao executemany (não confundir com rowcount).
    """
    itens = [p for p in produtos if p.get("id_bling")]
    if not itens:
        return 0

    try:
        params: List[Tuple] = [_params_upsert(p) for p in itens]
        cursor.executemany(_SQL_UPSERT, params)
        return len(params)
    except mysql.connector.Error as e:
        logger.error("Erro durante upsert em lote: %s", e)
        raise


def needs_details(cursor, id_bling: int, max_age_hours: int) -> bool:
    """Determina se os detalhes do produto devem ser buscados/atualizados.

    Verdadeiro quando:
    - imagem é nula/vazia, ou
    - data_alteracao é nula, ou
    - data_alteracao é mais antiga que NOW() - max_age_hours.
    """
    cursor.execute(
        """
        SELECT
            (imagem IS NULL OR imagem = '') AS img_vazia,
            (data_alteracao IS NULL OR data_alteracao < (NOW() - INTERVAL %s HOUR)) AS stale
        FROM produtos_bling
        WHERE id_bling = %s
        """,
        (int(max_age_hours), int(id_bling))
    )
    row = cursor.fetchone()
    if row is None:
        return True
    img_vazia, stale = row
    return bool(img_vazia or stale)
