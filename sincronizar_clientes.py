from typing import List, Dict
from mysql.connector import MySQLConnection
import mysql.connector
from db import conectar_mysql
from bling_clientes import buscar_clientes, buscar_detalhes_cliente
from logger import logger
from datetime import datetime, timezone
import re

def _criar_tabela_clientes(conn: MySQLConnection) -> None:
    """Cria a tabela de clientes se não existir."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes_bling (
                id BIGINT(20) NOT NULL AUTO_INCREMENT,
                codigo BIGINT(20) DEFAULT NULL,
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
                PRIMARY KEY (`id`)
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

def _to_upper(valor):
    """Converte valores de texto para UPPERCASE mantendo None quando aplicável."""
    if valor is None:
        return None
    try:
        return str(valor).upper().strip()
    except Exception:
        return valor

def _parse_datetime(value: str):
    """Tenta converter uma string de data/hora de API para datetime (naive, UTC)."""
    if not value:
        return None
    s = str(value).strip()
    try:
        # Normaliza Z -> +00:00
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        # Normaliza offsets como -0300 para -03:00
        m = re.search(r"([+-]\d{2})(\d{2})$", s)
        if m and ':' not in s[-6:]:
            s = s[:-5] + f"{m.group(1)}:{m.group(2)}"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        # Tenta alguns formatos comuns
        for fmt in (
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = datetime.strptime(s, fmt)
                if "%z" in fmt and dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except Exception:
                continue
    return None

def _api_data_alteracao(cliente: Dict):
    """Extrai a data de alteração do cliente vindo da API, se disponível."""
    for key in (
        'atualizadoEm', 'dataAlteracao', 'data_alteracao',
        'updatedAt', 'updated_at', 'dataAtualizacao', 'alteradoEm'
    ):
        if key in cliente and cliente.get(key):
            return _parse_datetime(cliente.get(key))
    # Alguns retornos podem ter metadata: { atualizadoEm: ... }
    meta = cliente.get('metadata') or cliente.get('meta') or {}
    for key in (
        'atualizadoEm', 'dataAlteracao', 'data_alteracao',
        'updatedAt', 'updated_at', 'dataAtualizacao', 'alteradoEm'
    ):
        if key in meta and meta.get(key):
            return _parse_datetime(meta.get(key))
    return None

def _deve_atualizar(cursor, id_cliente: int, api_dt):
    """Retorna True se deve inserir/atualizar com base na comparação de datas.
    - Se não existe no banco: True (inserir)
    - Se api_dt é None e registro já existe: False (não atualizar por falta de referência)
    - Se api_dt > data_alteracao do banco: True, caso contrário False
    """
    try:
        cursor.execute("SELECT data_alteracao FROM clientes_bling WHERE id = %s", (id_cliente,))
        row = cursor.fetchone()
        if row is None:
            return True
        db_dt = row[0]  # datetime do MySQL (naive)
        if api_dt is None:
            return False
        return api_dt > db_dt
    except Exception as e:
        logger.warning(f"Falha ao comparar data_alteracao para id={id_cliente}: {e}. Prosseguindo com atualização.")
        return True

def _inserir_ou_atualizar_cliente(cursor, cliente: Dict) -> bool:
    """Insere ou atualiza um cliente no banco de dados.

    Implementa o mapeamento conforme estrutura padrão do retorno do endpoint /contatos (exemplo.json):
    - Campos raiz: fantasia, tipo, ie, rg, email
    - Endereço: endereco.geral (fallback para endereco.cobranca)
      com: endereco, numero, complemento, bairro, cep, municipio, uf
    """
    try:
        # Extrai o endereço geral do cliente, com fallback para cobranca
        _endereco = (cliente.get('endereco') or {})
        endereco = (_endereco.get('geral') or {})
        if not endereco:
            endereco = (_endereco.get('cobranca') or {})
        
        # Limpa os campos numéricos
        documento = _limpar_campo(cliente.get('numeroDocumento'))
        ie = _limpar_campo(cliente.get('ie'))
        telefone = _limpar_campo(cliente.get('telefone'))
        celular = _limpar_campo(cliente.get('celular'))
        
        sql = """
            INSERT INTO clientes_bling (
                id, codigo, nome, fantasia, tipo, documento, ie, rg,
                telefone, celular, email, endereco, numero, complemento,
                bairro, cep, municipio, uf, situacao
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
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
                situacao = VALUES(situacao);
        """
        
        # Parâmetros corretos (19 valores) com conversão de campos de texto para UPPERCASE
        params = (
            cliente.get('id'),
            cliente.get('codigo'),
            _to_upper(cliente.get('nome')),
            _to_upper(cliente.get('fantasia')),
            _to_upper(cliente.get('tipo')),
            documento,
            ie,
            _to_upper(cliente.get('rg')),
            _limpar_campo(cliente.get('telefone')),
            _limpar_campo(cliente.get('celular')),
            _to_upper(cliente.get('email')),
            _to_upper(endereco.get('endereco')),
            _to_upper(endereco.get('numero')),
            _to_upper(endereco.get('complemento')),
            _to_upper(endereco.get('bairro')),
            (_endereco.get('geral') or {}).get('cep') or (_endereco.get('cobranca') or {}).get('cep'),
            _to_upper(endereco.get('municipio')),
            _to_upper(endereco.get('uf')),
            _to_upper(cliente.get('situacao', 'A'))
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
                
                # Sempre busca os detalhes completos do cliente pelo ID
                detalhes = buscar_detalhes_cliente(cliente_id)
                if detalhes:
                    logger.debug(f"Detalhes obtidos para cliente {cliente_id}")
                    cliente = detalhes
                else:
                    logger.warning(f"Não foi possível obter detalhes do cliente {cliente_id}; prosseguindo com dados simplificados da listagem")
                
                # Validação: apenas atualizar se API estiver mais recente que o banco
                api_dt = _api_data_alteracao(cliente)
                if not _deve_atualizar(cursor, cliente_id, api_dt):
                    logger.debug(f"Pulado update do cliente {cliente_id}: banco mais recente/igual à API")
                    continue
                
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