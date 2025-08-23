import requests
from time import sleep
from typing import List, Dict, Optional
from logger import logger
from bling_api import _get_auth_headers

def buscar_clientes(pagina: int = 1) -> List[Dict]:
    """Busca clientes na API v3 do Bling.

    Args:
        pagina (int): Número da página a ser buscada.

    Returns:
        List[Dict]: Lista de clientes retornados pela API.
    """
    try:
        url = "https://www.bling.com.br/Api/v3/contatos"
        params = {
            'pagina': pagina,
            'limite': 100,
            'criterio': 'cadastro',
            'ordem': 'DESC'
        }
        
        # Adiciona timeout e retry
        max_retries = 3
        retry_delay = 5
        timeout = 30
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=_get_auth_headers(),
                    timeout=timeout
                )
                response.raise_for_status()
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        return data['data']
                    return []
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Timeout ao buscar clientes. Tentativa {attempt + 1} de {max_retries}. "
                        f"Aguardando {retry_delay} segundos..."
                    )
                    sleep(retry_delay)
                    continue
                else:
                    logger.error("Erro de timeout após todas as tentativas")
                    raise
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Erro ao buscar clientes: {e}. Tentativa {attempt + 1} de {max_retries}. "
                        f"Aguardando {retry_delay} segundos..."
                    )
                    sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Erro após todas as tentativas: {e}")
                    raise
                    
        return []
        
    except Exception as e:
        logger.error(f"Erro ao buscar clientes: {e}")
        return []

def buscar_detalhes_cliente(id_cliente: int) -> Optional[Dict]:
    """Busca detalhes de um cliente específico na API v3 do Bling.

    Args:
        id_cliente (int): ID do cliente no Bling.

    Returns:
        Optional[Dict]: Detalhes do cliente ou None em caso de erro.
    """
    try:
        url = f"https://www.bling.com.br/Api/v3/contatos/{id_cliente}"
        
        # Adiciona timeout e retry
        max_retries = 3
        retry_delay = 5
        timeout = 30
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    headers=_get_auth_headers(),
                    timeout=timeout
                )
                response.raise_for_status()
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data:
                        return data['data']
                    return None
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Timeout ao buscar detalhes do cliente {id_cliente}. "
                        f"Tentativa {attempt + 1} de {max_retries}. Aguardando {retry_delay} segundos..."
                    )
                    sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Erro de timeout após todas as tentativas para o cliente {id_cliente}")
                    raise
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Erro ao buscar detalhes do cliente {id_cliente}: {e}. "
                        f"Tentativa {attempt + 1} de {max_retries}. Aguardando {retry_delay} segundos..."
                    )
                    sleep(retry_delay)
                    continue
                else:
                    logger.error(f"Erro após todas as tentativas para o cliente {id_cliente}: {e}")
                    raise
                    
        return None
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do cliente {id_cliente}: {e}")
        return None