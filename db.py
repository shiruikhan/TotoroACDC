# Módulo de interação com o banco de dados MySQL

# Importações necessárias
import os  # Para variáveis de ambiente
from typing import Any, Iterable, List, Tuple  # Para type hints
import mysql.connector  # Driver MySQL
from dotenv import load_dotenv  # Para carregar variáveis de ambiente
from logger import logger  # Para logging

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

def conectar_mysql():
    """Estabelece conexão com o banco de dados MySQL.
    
    Utiliza variáveis de ambiente para configuração:
    - DB_HOST: Host do banco
    - DB_PORT: Porta (default: 3306)
    - DB_USER: Usuário
    - DB_PASSWORD: Senha
    - DB_NAME: Nome do banco
    
    Returns:
        MySQLConnection: Conexão com o banco de dados
    
    Raises:
        RuntimeError: Se faltarem variáveis de ambiente obrigatórias
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
    faltando = [k for k in ("host","user","password","database") if not cfg[k]]
    if faltando:
        raise RuntimeError(f"Variáveis de ambiente ausentes: {', '.join(faltando)}")
    conn = mysql.connector.connect(**cfg)
    # Melhora desempenho em lote:
    conn.autocommit = False
    logger.info("Conectado ao banco %s:%s/%s", cfg["host"], cfg["port"], cfg["database"])
    return conn

def _to_float(value: Any) -> float:
    """Converte um valor para float de forma segura.
    
    Args:
        value (Any): Valor a ser convertido
    
    Returns:
        float: Valor convertido ou 0.0 em caso de erro
    """
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))  # Converte vírgula para ponto
    except (ValueError, TypeError):
        return 0.0

def _to_int(value: Any) -> int:
    """Converte um valor para inteiro de forma segura.
    
    Args:
        value (Any): Valor a ser convertido
    
    Returns:
        int: Valor convertido ou 0 em caso de erro
    """
    try:
        return int(float(str(value).replace(",", ".")))  # Converte para float primeiro
    except (ValueError, TypeError):
        return 0

_SQL_UPSERT = """
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

def _params_upsert(produto: dict) -> Tuple:
    """Prepara os parâmetros para a query de upsert.
    
    Converte e formata os valores do produto para o formato esperado pelo banco.
    
    Args:
        produto (dict): Dicionário com dados do produto
    
    Returns:
        Tuple: Tupla com valores formatados na ordem da query SQL
    """
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
    """Insere ou atualiza um único produto no banco.
    
    Mantido para compatibilidade com código legado. Para melhor performance,
    prefira usar upsert_batch para múltiplos produtos.
    
    Args:
        cursor: Cursor do MySQL
        produto (dict): Dados do produto
    
    Returns:
        bool: True se sucesso, False se erro
    """
    try:
        cursor.execute(_SQL_UPSERT, _params_upsert(produto))
        return True
    except Exception as e:
        logger.error("Falha ao inserir/atualizar id_bling=%s: %s", produto.get("id_bling"), e)
        return False

def upsert_batch(cursor, produtos: Iterable[dict]) -> int:
    """Insere ou atualiza múltiplos produtos em lote.
    
    Utiliza executemany para melhor performance. O commit deve ser feito
    explicitamente após a chamada desta função.
    
    Args:
        cursor: Cursor do MySQL
        produtos (Iterable[dict]): Lista de produtos
    
    Returns:
        int: Número de produtos processados
    """
    itens = [p for p in produtos if p.get("id_bling")]
    if not itens:
        return 0

    try:
        # Prepara os parâmetros para inserção
        params: List[Tuple] = [_params_upsert(p) for p in itens]
        
        # Registra quantidade de itens a serem inseridos
        logger.warning(f"Tentando inserir {len(params)} produtos em lote")
        
        # Executa o upsert em lote
        cursor.executemany(_SQL_UPSERT, params)
        
        # Verifica se a quantidade esperada foi processada
        affected_rows = cursor.rowcount
        logger.warning(f"Rows afetadas pelo upsert: {affected_rows}")
        
        return len(params)
        
    except mysql.connector.Error as e:
        logger.error(f"Erro durante upsert em lote: {e}")
        raise

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
        FROM produtos_bling
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
