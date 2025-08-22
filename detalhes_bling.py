from bling_api import buscar_detalhes_produto
from datetime import datetime
from logger import logger

def _num(value):
    """Converte um valor para float de forma segura.
    
    Args:
        value: Valor a ser convertido para float
    
    Returns:
        float: Valor convertido ou 0.0 em caso de erro
    """
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

def _extract_details(produto: dict) -> dict:
    """Extrai detalhes relevantes do produto retornado pela API.
    
    Args:
        produto (dict): Dicionário com dados do produto da API
    
    Returns:
        dict: Dicionário com detalhes extraídos
    """   
    
    # Extrai dimensões
    dimensoes = produto.get('dimensoes', {})
    
    # Extrai dados de preço
    preco = 0
    if isinstance(produto.get('preco'), dict):
        preco = _num(produto['preco'].get('preco', 0))
    else:
        preco = _num(produto.get('preco', 0))
           
    # Extrai imagem do produto
    imagem = None
    midia = produto.get('midia', {})
    imagens = midia.get('imagens', {})
    internas = imagens.get('internas', [])
    if internas and isinstance(internas, list) and len(internas) > 0:
        primeiro_item = internas[0]
        if isinstance(primeiro_item, dict):
            imagem = primeiro_item.get('link')
    
    return {
        "estoque": (produto.get("estoque") or {}).get("saldoVirtualTotal", 0),
        "preco": preco,
        "largura": _num(dimensoes.get('largura')),
        "altura": _num(dimensoes.get('altura')),
        "profundidade": _num(dimensoes.get('profundidade')),
        "peso_liquido": produto.get('pesoLiquido'),
        "peso_bruto": produto.get('pesoBruto'),
        "imagem": imagem
    }

def update_product_details(cursor, id_bling: int) -> bool:
    """Atualiza os detalhes de um produto específico.
    
    Args:
        cursor: Cursor do banco de dados
        id_bling (int): ID do produto no Bling
    
    Returns:
        bool: True se atualizado com sucesso, False caso contrário
    """
    try:
        # Busca detalhes do produto na API
        produto = buscar_detalhes_produto(id_bling)
        if not produto:
            logger.warning(f"Detalhes não encontrados para produto {id_bling}")
            return False

        # Extrai detalhes relevantes
        detalhes = _extract_details(produto)

        # Monta a query de atualização
        sql = """
            UPDATE produtos_bling
            SET estoque = %s,
                preco = %s,
                largura = %s,
                altura = %s,
                profundidade = %s,
                peso_liquido = %s,
                peso_bruto = %s,
                imagem = %s,
                data_alteracao = %s
            WHERE id_bling = %s
        """

        # Executa a atualização
        cursor.execute(
            sql,
            (
                detalhes["estoque"],
                detalhes["preco"],
                detalhes["largura"],
                detalhes["altura"],
                detalhes["profundidade"],
                detalhes["peso_liquido"],
                detalhes["peso_bruto"],
                detalhes["imagem"],
                datetime.now(),
                id_bling
            )
        )

        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar detalhes do produto {id_bling}: {e}")
        return False
