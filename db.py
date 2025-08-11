from logger import logger
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error as MySQLError
from decimal import Decimal

load_dotenv()

def _safe_float(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    s = str(value).strip().replace(",", ".")
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0

def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")

def conectar_mysql():
    host = os.getenv("DB_HOST")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")

    # Diagnostic: driver options via env
    # DB_USE_PURE=true|false (default true to avoid opaque C-extension error)
    # DB_AUTH_PLUGIN= mysql_native_password | caching_sha2_password | ...
    # DB_SSL_MODE= DISABLED | REQUIRED
    # DB_SSL_CA= path to CA file (if provided, SSL will be enabled with this CA)
    use_pure = _bool_env("DB_USE_PURE", True)
    auth_plugin = os.getenv("DB_AUTH_PLUGIN")
    ssl_mode = (os.getenv("DB_SSL_MODE") or "").upper()
    ssl_ca = os.getenv("DB_SSL_CA")

    params = dict(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connection_timeout=10,
        use_pure=use_pure,
    )

    if auth_plugin:
        params["auth_plugin"] = auth_plugin

    if ssl_mode == "DISABLED":
        params["ssl_disabled"] = True
    elif ssl_ca:
        params["ssl_ca"] = ssl_ca
    elif ssl_mode == "REQUIRED":
        # When required but no CA provided, let connector negotiate default SSL
        # (server must present certificate trusted by OS store)
        pass

    logger.info(
        "Connecting to database host=%s port=%s db=%s user=%s use_pure=%s auth_plugin=%s ssl_mode=%s ssl_ca=%s",
        host, port, database, user, use_pure, auth_plugin or "-", ssl_mode or "-", "set" if ssl_ca else "-"
    )

    try:
        conn = mysql.connector.connect(**params)
        logger.info("Database connection established")
        return conn
    except MySQLError as e:
        # Log rich diagnostics without secrets
        try:
            err_no = getattr(e, "errno", None)
            sqlstate = getattr(e, "sqlstate", None)
            msg = getattr(e, "msg", str(e))
            logger.error("MySQL error errno=%s sqlstate=%s msg=%s", err_no, sqlstate, msg)
        except Exception:
            logger.exception("Unexpected error object while logging MySQL error")
        raise
    except Exception:
        logger.exception("Database connection failed with non-MySQL error")
        raise

def criar_tabela(cursor):
    cursor.execute("""            CREATE TABLE IF NOT EXISTS temp_produtos_bling (
            id_bling BIGINT PRIMARY KEY,
            codigo VARCHAR(255),
            nome VARCHAR(255),
            preco DECIMAL(10,2),
            estoque DECIMAL(10,2),
            tipo VARCHAR(45),
            situacao VARCHAR(45),
            formato VARCHAR(45)
        )
    """        )

def inserir_ou_atualizar(cursor, produto, conn):
    try:
        cursor.execute(
            "SELECT codigo, nome, preco, estoque, tipo, situacao, formato FROM temp_produtos_bling WHERE id_bling = %s",
            (produto["id_bling"],),
        )
        resultado = cursor.fetchone()

        if resultado:
            codigo, nome, preco, saldo, tipo, situacao, formato = resultado
            if (
                codigo == produto.get("codigo")
                and nome == produto.get("nome")
                and _safe_float(preco) == _safe_float(produto.get("preco"))
                and _safe_float(saldo) == _safe_float(produto.get("estoque"))
                and tipo == produto.get("tipo")
                and situacao == produto.get("situacao")
                and formato == produto.get("formato")
            ):
                return False  # no change

        cursor.execute(
            """                INSERT INTO temp_produtos_bling (id_bling, codigo, nome, preco, estoque, tipo, situacao, formato)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                codigo = VALUES(codigo),
                nome = VALUES(nome),
                preco = VALUES(preco),
                estoque = VALUES(estoque),
                tipo = VALUES(tipo),
                situacao = VALUES(situacao),
                formato = VALUES(formato)
            """,                (
                produto["id_bling"],
                produto.get("codigo"),
                produto.get("nome"),
                _safe_float(produto.get("preco")),
                _safe_float(produto.get("estoque")),
                produto.get("tipo"),
                produto.get("situacao"),
                produto.get("formato"),
            ),
        )
        return True
    except Exception:
        pid = produto.get("id_bling")
        logger.exception("Insert or update failed for product id=%s", pid)
        return False
