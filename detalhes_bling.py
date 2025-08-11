from typing import Any
from dotenv import load_dotenv
from logger import logger
from bling_api import buscar_detalhe_produto

load_dotenv()

def _num(x: Any) -> float:
    if x is None:
        return 0.0
    try:
        return float(str(x).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0

def _extract_details(data: dict) -> dict:
    dimensoes = data.get("dimensoes") or {}
    largura = _num(dimensoes.get("largura") or dimensoes.get("larguraCm") or data.get("largura"))
    altura = _num(dimensoes.get("altura") or dimensoes.get("alturaCm") or data.get("altura"))
    profundidade = _num(dimensoes.get("profundidade") or dimensoes.get("comprimento") or data.get("profundidade"))

    pesos = data.get("pesos") or {}
    peso_liquido = _num(pesos.get("liquido") or pesos.get("pesoLiquido") or data.get("peso_liquido"))
    peso_bruto = _num(pesos.get("bruto") or pesos.get("pesoBruto") or data.get("peso_bruto"))

    # IMAGEM: midia > imagens > internas[0].link -> externas[0].link -> imagensURL[0]
    imagem = None
    midia = data.get("midia") or {}
    imgs = (midia.get("imagens") or {})
    internas = imgs.get("internas") or []
    externas = imgs.get("externas") or []
    imagens_url = imgs.get("imagensURL") or []

    if not imagem and isinstance(internas, list) and internas:
        first = internas[0]
        if isinstance(first, dict):
            imagem = first.get("link") or first.get("url")

    if not imagem and isinstance(externas, list) and externas:
        first = externas[0]
        if isinstance(first, dict):
            imagem = first.get("link") or first.get("url")

    if not imagem and isinstance(imagens_url, list) and imagens_url:
        if isinstance(imagens_url[0], str):
            imagem = imagens_url[0]

    if not imagem:
        bruto = imgs.get("link") or imgs.get("url") or data.get("imagem")
        if isinstance(bruto, str):
            imagem = bruto
        elif isinstance(bruto, dict):
            imagem = bruto.get("link") or bruto.get("url")

    situacao = str((data.get("situacao") or data.get("status") or "")).strip()[:1]

    return {
        "largura": largura,
        "altura": altura,
        "profundidade": profundidade,
        "peso_liquido": peso_liquido,
        "peso_bruto": peso_bruto,
        "imagem": imagem,
        "situacao": situacao,
    }

def update_product_details(cursor, id_bling: int, table_name: str = "temp_produtos_bling") -> bool:
    detail = buscar_detalhe_produto(id_bling)
    if not detail:
        return False

    fields = _extract_details(detail)
    sql = f"""
        UPDATE {table_name}
           SET largura        = %s,
               altura         = %s,
               profundidade   = %s,
               peso_liquido   = %s,
               peso_bruto     = %s,
               imagem         = %s,
               situacao       = %s,
               data_alteracao = NOW()
         WHERE id_bling = %s
    """
    params = (
        fields["largura"],
        fields["altura"],
        fields["profundidade"],
        fields["peso_liquido"],
        fields["peso_bruto"],
        fields["imagem"],
        fields["situacao"],
        int(id_bling),
    )
    try:
        cursor.execute(sql, params)
        return True
    except Exception as e:
        logger.error("Falha ao atualizar detalhes (%s): %s", id_bling, e)
        return False
