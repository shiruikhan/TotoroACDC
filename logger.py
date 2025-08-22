# Módulo de configuração de logging para a integração com o Bling

# Importações necessárias
import logging  # Módulo de logging padrão do Python
import os  # Para acessar variáveis de ambiente

# Configurações de logging através de variáveis de ambiente
LOG_FILE = os.getenv("LOG_FILE", "integracao_bling.log")  # Arquivo de log
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()  # Nível de log (WARNING por padrão para reduzir verbosidade)

# Criação e configuração do logger
logger = logging.getLogger("bling_sync")  # Logger específico para sincronização

# Configura handlers apenas se não existirem (evita duplicação)
if not logger.handlers:
    # Define o nível de log global
    logger.setLevel(LOG_LEVEL)

    # Define o formato das mensagens de log
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Handler para arquivo
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")  # Salva logs em arquivo
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Handler para console
    ch = logging.StreamHandler()  # Exibe logs no console
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
