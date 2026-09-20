"""
CyberHeist Bot - Logging Configuration
======================================
Module ini menyediakan logging configuration yang konsisten untuk
seluruh bot. Semua log akan ditulis ke console DAN ke file log
dengan rotasi otomatis (max 5 file @ 5MB each).

Pemakaian di file lain:
    from logger import get_logger
    logger = get_logger(__name__)
    logger.info("Bot started")
    logger.error("Something went wrong", exc_info=True)
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import sys

# Buat folder logs/ kalau belum ada
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOGS_DIR = os.path.join(_BASE_DIR, "logs")
os.makedirs(_LOGS_DIR, exist_ok=True)

# Format log yang informatif
_LOG_FORMAT = logging.Formatter(
    fmt="[{asctime}] [{levelname:^8}] {name}: {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{"
)

# Handler untuk console (stdout)
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_LOG_FORMAT)

# Handler untuk file dengan rotasi otomatis
# maxBytes=5MB, backupCount=5 -> max total 25MB log files
_file_handler = RotatingFileHandler(
    filename=os.path.join(_LOGS_DIR, "cyberheist.log"),
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setLevel(logging.DEBUG)  # File log semua level
_file_handler.setFormatter(_LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """
    Mendapatkan logger instance dengan nama tertentu.
    Logger otomatis sudah terhubung ke console dan file handler.

    Args:
        name: Nama logger, biasanya __name__ dari module yang memanggilnya.

    Returns:
        logging.Logger instance yang sudah dikonfigurasi.
    """
    logger = logging.getLogger(name)

    # Set level default ke DEBUG (handler-nya yang filter)
    logger.setLevel(logging.DEBUG)

    # Cegah duplikasi handler jika get_logger dipanggil berkali-kali
    if not logger.handlers:
        logger.addHandler(_console_handler)
        logger.addHandler(_file_handler)

    # Jangan propagate ke root logger (cegah double logging)
    logger.propagate = False

    return logger
