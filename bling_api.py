"""Cliente simples para consumo da API v3 do Bling (produtos)."""
import os
from time import sleep

import requests
from dotenv import load_dotenv
from logger import logger

load_dotenv()


def _get_auth_headers():
    """Headers de autenticação (Bearer) para chamadas à API do Bling."""
    return {
        "Authorization": f"Bearer {os.getenv('BLING_ACCESS_TOKEN')}",
        "Accept": "application/json",
    }


def buscar_produtos(pagina: int = 1):
    """Busca a página informada de produtos.

    Args:
        pagina: número da página (1-based)

    Returns:
        list: lista de produtos (cada item é um dict).
    """
    url = "https://www.bling.com.br/Api/v3/produtos"
    params = {"pagina": pagina, "limite": 100, "criterio": "cadastro", "ordem": "DESC"}

    max_retries, retry_delay, timeout = 3, 5, 30

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=_get_auth_headers(), timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                logger.warning(
                    "Timeout ao buscar produtos (página %s). Tentativa %s/%s. Aguardando %ss...",
                    pagina,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Timeout definitivo ao buscar produtos (página %s)", pagina)
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "Erro ao buscar produtos (página %s): %s. Tentativa %s/%s. Aguardando %ss...",
                    pagina,
                    e,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Erro ao buscar produtos (página %s): %s", pagina, e)
            break
        except ValueError:
            logger.error("Resposta inválida (não JSON) para produtos (página %s)", pagina)
            break
    return []


def buscar_detalhes_produto(id_produto: int):
    """Busca os detalhes de um produto específico.

    Returns:
        dict | None: Detalhes do produto ou None em caso de erro/ausência.
    """
    url = f"https://www.bling.com.br/Api/v3/produtos/{id_produto}"
    max_retries, retry_delay, timeout = 3, 5, 30

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=_get_auth_headers(), timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data")
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                logger.warning(
                    "Timeout ao buscar detalhes do produto %s. Tentativa %s/%s. Aguardando %ss...",
                    id_produto,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Timeout definitivo ao buscar detalhes do produto %s", id_produto)
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "Erro ao buscar detalhes do produto %s: %s. Tentativa %s/%s. Aguardando %ss...",
                    id_produto,
                    e,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Erro ao buscar detalhes do produto %s: %s", id_produto, e)
            break
        except ValueError:
            logger.error("Resposta inválida (não JSON) para detalhes do produto %s", id_produto)
            break
    return None
