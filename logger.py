import logging
import os

LOG_FILE = os.getenv("LOG_FILE", "integracao_bling.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.WARNING,  # consolidated to WARNING
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)

logger = logging.getLogger("bling_sync")
