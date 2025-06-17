from logger import logger
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def conectar_mysql():
    logger.info(f"Conectado ao banco: {os.getenv('DB_NAME')}")
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def criar_tabela(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produto (
            id INT PRIMARY KEY,
            codigo VARCHAR(255),
            nome VARCHAR(255),
            preco DECIMAL(10,2),
            saldovirtualtotal DECIMAL(10,2)
        )
    """)

def inserir_ou_atualizar(cursor, produto, conn):
    try:
        cursor.execute("SELECT codigo, nome, preco, saldovirtualtotal FROM produto WHERE id = %s", (produto["id"],))
        resultado = cursor.fetchone()

        if resultado:
            codigo, nome, preco, saldo = resultado
            if (
                codigo == produto["codigo"] and
                nome == produto["nome"] and
                float(preco) == float(produto["preco"]) and
                float(saldo) == float(produto["saldovirtualtotal"])
            ):
                return False  # Nenhuma alteração

        cursor.execute("""
            INSERT INTO produto (id, codigo, nome, preco, saldovirtualtotal)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                codigo = VALUES(codigo),
                nome = VALUES(nome),
                preco = VALUES(preco),
                saldovirtualtotal = VALUES(saldovirtualtotal)
        """, (
            produto["id"],
            produto["codigo"],
            produto["nome"],
            produto["preco"],
            produto["saldovirtualtotal"]
        ))
        return True
    except Exception as e:
        logger.error(f"[ERRO] Falha ao inserir/atualizar produto ID={produto['id']}: {e}")
        return False
