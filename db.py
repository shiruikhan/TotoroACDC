import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def conectar_mysql():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def criar_tabela(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos_bling (
            id INT PRIMARY KEY,
            codigo VARCHAR(255),
            nome VARCHAR(255),
            preco DECIMAL(10,2),
            saldo_virtual_total DECIMAL(10,2)
        )
    """)

def inserir_ou_atualizar(cursor, produto):
    cursor.execute("""
        INSERT INTO produtos_bling (id, codigo, nome, preco, saldo_virtual_total)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            codigo = VALUES(codigo),
            nome = VALUES(nome),
            preco = VALUES(preco),
            saldo_virtual_total = VALUES(saldo_virtual_total)
    """, (
        produto["id"],
        produto["codigo"],
        produto["nome"],
        produto["preco"],
        produto["saldo_virtual_total"]
    ))
