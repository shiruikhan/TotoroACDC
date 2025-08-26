"""Atualização de detalhes de produto (dimensões, preços, imagem) a partir do Bling."""
from datetime import datetime

from bling_api import buscar_detalhes_produto
from logger import logger


def _num(value):
    """Converte texto/None para float, aceitando vírgula decimal."""
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def _extract_details(produto: dict) -> dict:
    """Extrai detalhes relevantes do payload do produto da API."""
    dimensoes = produto.get("dimensoes", {})

    # Preço pode vir como dict ou valor simples
    if isinstance(produto.get("preco"), dict):
        preco = _num(produto["preco"].get("preco", 0))
    else:
        preco = _num(produto.get("preco", 0))

    # Imagem principal (primeira imagem interna se existir)
    imagem = None
    midia = produto.get("midia", {})
    imagens = midia.get("imagens", {})
    internas = imagens.get("internas", [])
    if internas and isinstance(internas, list):
        primeiro_item = internas[0]
        if isinstance(primeiro_item, dict):
            imagem = primeiro_item.get("link")

    return {
        "estoque": (produto.get("estoque") or {}).get("saldoVirtualTotal", 0),
        "preco": preco,
        "largura": _num(dimensoes.get("largura")),
        "altura": _num(dimensoes.get("altura")),
        "profundidade": _num(dimensoes.get("profundidade")),
        "peso_liquido": produto.get("pesoLiquido"),
        "peso_bruto": produto.get("pesoBruto"),
        "imagem": imagem,
    }


def update_product_details(cursor, id_bling: int) -> bool:
    """Busca detalhes no Bling e atualiza o registro em produtos_bling.

    Returns:
        bool: True se atualizado com sucesso; False caso contrário.
    """
    try:
        produto = buscar_detalhes_produto(id_bling)
        if not produto:
            logger.warning("Detalhes não encontrados para produto %s", id_bling)
            return False

        detalhes = _extract_details(produto)

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
                id_bling,
            ),
        )
        return True
    except Exception as e:
        logger.error("Erro ao atualizar detalhes do produto %s: %s", id_bling, e)
        return False
