"""
logger.py
=========
Sistema centralizado de logging con salida a consola y a fichero rotativo.
Cada ejecución del pipeline genera una entrada con timestamp en logs/.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_DIR

os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """
    Devuelve un logger configurado con:
    - Consola (nivel INFO)
    - Fichero rotativo en logs/pipeline.log (nivel DEBUG, máx 5 MB x 3 backups)
    """
    logger = logging.getLogger(name)

    # Evitar duplicar handlers si el logger ya fue inicializado
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler consola
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # Handler fichero rotativo
    log_file = os.path.join(LOG_DIR, "pipeline.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
