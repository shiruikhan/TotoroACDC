import logging
import os

LOG_FILE = os.getenv("LOG_FILE", "integracao_bling.log")
# Reduz verbosidade: WARNING por padrão
LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()

logger = logging.getLogger("bling_sync")
if not logger.handlers:
    logger.setLevel(LOG_LEVEL)

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
