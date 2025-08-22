import requests
import os
from dotenv import load_dotenv
from time import sleep

load_dotenv()

def _get_auth_headers():
    """Retorna os headers de autenticação para a API v3 do Bling."""
    return {
        'Authorization': f'Bearer {os.getenv("BLING_ACCESS_TOKEN")}',
        'Accept': 'application/json'
    }

def buscar_produtos(pagina=1):
    """Busca produtos na API v3 do Bling.

    Args:
        pagina (int): Número da página a ser buscada.

    Returns:
        list: Lista de produtos retornados pela API.
    """
    try:
        url = f"https://www.bling.com.br/Api/v3/produtos"
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
                    print(f"Timeout ao buscar produtos. Tentativa {attempt + 1} de {max_retries}. Aguardando {retry_delay} segundos...")
                    sleep(retry_delay)
                    continue
                else:
                    print("Erro de timeout após todas as tentativas")
                    raise
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Erro ao buscar produtos: {e}. Tentativa {attempt + 1} de {max_retries}. Aguardando {retry_delay} segundos...")
                    sleep(retry_delay)
                    continue
                else:
                    print(f"Erro após todas as tentativas: {e}")
                    raise
                    
        return []
        
    except Exception as e:
        print(f"Erro ao buscar produtos: {e}")
        return []

def buscar_detalhes_produto(id_produto):
    """Busca detalhes de um produto específico na API v3 do Bling.

    Args:
        id_produto (int): ID do produto no Bling.

    Returns:
        dict: Detalhes do produto ou None em caso de erro.
    """
    try:
        url = f"https://www.bling.com.br/Api/v3/produtos/{id_produto}"
        
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
                    print(f"Timeout ao buscar detalhes do produto {id_produto}. Tentativa {attempt + 1} de {max_retries}. Aguardando {retry_delay} segundos...")
                    sleep(retry_delay)
                    continue
                else:
                    print(f"Erro de timeout após todas as tentativas para o produto {id_produto}")
                    raise
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Erro ao buscar detalhes do produto {id_produto}: {e}. Tentativa {attempt + 1} de {max_retries}. Aguardando {retry_delay} segundos...")
                    sleep(retry_delay)
                    continue
                else:
                    print(f"Erro após todas as tentativas para o produto {id_produto}: {e}")
                    raise
                    
        return None
        
    except Exception as e:
        print(f"Erro ao buscar detalhes do produto {id_produto}: {e}")
        return None
