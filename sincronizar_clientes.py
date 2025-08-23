from typing import List, Dict
from mysql.connector import MySQLConnection
import mysql.connector
from db import conectar_mysql
from bling_clientes import buscar_clientes, buscar_detalhes_cliente
from logger import logger

def _criar_tabela_clientes(conn: MySQLConnection) -> None:
    """Cria a tabela de clientes se não existir."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes_bling (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo VARCHAR(50),
                nome VARCHAR(255) NOT NULL,
                fantasia VARCHAR(255),
                tipo CHAR(1) NOT NULL COMMENT 'F=Física, J=Jurídica',
                documento VARCHAR(20) COMMENT 'CPF ou CNPJ',
                ie VARCHAR(20) COMMENT 'Inscrição Estadual',
                rg VARCHAR(20),
                telefone VARCHAR(20),
                celular VARCHAR(20),
                email VARCHAR(255),
                endereco VARCHAR(255),
                numero VARCHAR(10),
                complemento VARCHAR(100),
                bairro VARCHAR(100),
                cep VARCHAR(10),
                municipio VARCHAR(100),
                uf CHAR(2),
                situacao CHAR(1) DEFAULT 'A' COMMENT 'A=Ativo, I=Inativo',
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_documento (documento),
                INDEX idx_situacao (situacao)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        conn.commit()
        logger.info("Tabela clientes_bling criada/verificada com sucesso")
    except Exception as e:
        logger.error(f"Erro ao criar tabela clientes_bling: {e}")
        raise
    finally:
        cursor.close()

def _limpar_campo(valor: str) -> str:
    """Remove pontuação e caracteres especiais, mantendo apenas números."""
    if not valor:
        return ""
    return ''.join(char for char in str(valor) if char.isdigit())

def _inserir_ou_atualizar_cliente(cursor, cliente: Dict) -> bool:
    """Insere ou atualiza um cliente no banco de dados."""
    try:
        # Extrai o endereço geral do cliente
        endereco = cliente.get('endereco', {}).get('geral', {})
        
        # Limpa os campos numéricos
        documento = _limpar_campo(cliente.get('numeroDocumento'))
        ie = _limpar_campo(cliente.get('ie'))
        telefone = _limpar_campo(cliente.get('telefone'))
        celular = _limpar_campo(cliente.get('celular'))
        
        sql = """
            INSERT INTO clientes_bling (
                codigo, nome, fantasia, tipo, documento, ie, rg,
                telefone, celular, email, endereco, numero, complemento,
                bairro, cep, municipio, uf, situacao
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                codigo = VALUES(codigo),
                nome = VALUES(nome),
                fantasia = VALUES(fantasia),
                tipo = VALUES(tipo),
                documento = VALUES(documento),
                ie = VALUES(ie),
                rg = VALUES(rg),
                telefone = VALUES(telefone),
                celular = VALUES(celular),
                email = VALUES(email),
                endereco = VALUES(endereco),
                numero = VALUES(numero),
                complemento = VALUES(complemento),
                bairro = VALUES(bairro),
                cep = VALUES(cep),
                municipio = VALUES(municipio),
                uf = VALUES(uf),
                situacao = VALUES(situacao)
        """
        
        params = (
                cliente.get('codigo'),
                cliente.get('nome'),
                cliente.get('fantasia'),
                cliente.get('tipo'),  # F ou J
                documento,
                ie,
                cliente.get('rg'),
                telefone,
                celular,
            cliente.get('email'),
            endereco.get('endereco'),
            endereco.get('numero'),
            endereco.get('complemento'),
            endereco.get('bairro'),
            endereco.get('cep'),
            endereco.get('municipio'),
            endereco.get('uf'),
            cliente.get('situacao', 'A')  # A=Ativo por padrão
        )
        
        cursor.execute(sql, params)
        logger.debug(f"SQL executado com sucesso para cliente {cliente.get('id')}")
        return True
        
    except mysql.connector.Error as e:
        logger.error(f"Erro MySQL ao inserir/atualizar cliente {cliente.get('id')}: {e}")
        logger.error(f"Dados do cliente que causaram erro: {cliente}")
        return False
        
    except Exception as e:
        logger.error(f"Erro inesperado ao inserir/atualizar cliente {cliente.get('id')}: {e}")
        logger.error(f"Dados do cliente que causaram erro: {cliente}")
        return False

def sincronizar_clientes() -> None:
    """Sincroniza todos os clientes do Bling com o banco de dados."""
    logger.info("Iniciando sincronização de clientes do Bling")
    conn = conectar_mysql()
    try:
        # Cria a tabela se não existir
        _criar_tabela_clientes(conn)
        
        cursor = conn.cursor()
        pagina = 1
        total_sincronizado = 0
        logger.info("Buscando clientes do Bling - Página %d", pagina)
        
        while True:
            # Busca clientes da página atual
            clientes = buscar_clientes(pagina)
            if not clientes:
                logger.info("Não há mais clientes para sincronizar")
                break
                
            logger.info(f"Encontrados {len(clientes)} clientes na página {pagina}")
                
            # Processa cada cliente
            for cliente in clientes:
                cliente_id = cliente.get('id')
                logger.debug(f"Processando cliente ID: {cliente_id}")
                
                if _inserir_ou_atualizar_cliente(cursor, cliente):
                    total_sincronizado += 1
                    logger.debug(f"Cliente ID {cliente_id} sincronizado com sucesso")
                    
                    if total_sincronizado % 100 == 0:
                        logger.info(f"Sincronizados {total_sincronizado} clientes")
                        conn.commit()
                        logger.debug("Commit realizado no banco de dados")
            
            # Commit a cada página
            conn.commit()
            logger.info(f"Página {pagina} processada. Total sincronizado: {total_sincronizado}")
            
            pagina += 1
        
        logger.info(f"Sincronização concluída. Total de clientes sincronizados: {total_sincronizado}")
        
    except Exception as e:
        logger.error(f"Erro durante sincronização: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    sincronizar_clientes()