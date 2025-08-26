"""Cliente para endpoints de contatos da API v3 do Bling."""
from time import sleep
from typing import Dict, List, Optional

import requests
from logger import logger
from bling_api import _get_auth_headers


def buscar_clientes(pagina: int = 1) -> List[Dict]:
    """Busca clientes (paginado).

    Args:
        pagina: número da página (1-based)

    Returns:
        Lista de clientes (cada item é um dict).
    """
    url = "https://www.bling.com.br/Api/v3/contatos"
    params = {"pagina": pagina, "limite": 100, "criterio": "cadastro", "ordem": "DESC"}
    max_retries, retry_delay, timeout = 3, 5, 30

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=_get_auth_headers(), timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                logger.warning(
                    "Timeout ao buscar clientes (página %s). Tentativa %s/%s. Aguardando %ss...",
                    pagina,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Timeout definitivo ao buscar clientes (página %s)", pagina)
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "Erro ao buscar clientes (página %s): %s. Tentativa %s/%s. Aguardando %ss...",
                    pagina,
                    e,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Erro ao buscar clientes (página %s): %s", pagina, e)
            break
        except ValueError:
            logger.error("Resposta inválida (não JSON) para clientes (página %s)", pagina)
            break
    return []


def buscar_detalhes_cliente(id_cliente: int) -> Optional[Dict]:
    """Busca detalhes de um cliente específico.

    Returns:
        Dict | None: Detalhes do cliente, ou None se ausente/erro.
    """
    url = f"https://www.bling.com.br/Api/v3/contatos/{id_cliente}"
    max_retries, retry_delay, timeout = 3, 5, 30

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=_get_auth_headers(), timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("data")
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                logger.warning(
                    "Timeout ao buscar detalhes do cliente %s. Tentativa %s/%s. Aguardando %ss...",
                    id_cliente,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Timeout definitivo ao buscar detalhes do cliente %s", id_cliente)
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "Erro ao buscar detalhes do cliente %s: %s. Tentativa %s/%s. Aguardando %ss...",
                    id_cliente,
                    e,
                    attempt + 1,
                    max_retries,
                    retry_delay,
                )
                sleep(retry_delay)
                continue
            logger.error("Erro ao buscar detalhes do cliente %s: %s", id_cliente, e)
            break
        except ValueError:
            logger.error("Resposta inválida (não JSON) para detalhes do cliente %s", id_cliente)
            break
    return None