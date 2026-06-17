# app/core/logger.py
"""
Configuración centralizada de logging para Food Store API.
Usa exclusivamente la stdlib (logging estándar), sin dependencias adicionales.
"""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """
    Configura el logging global de la aplicación.
    Debe llamarse una sola vez al arrancar (en main.py).

    Args:
        level: Nivel de log ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        stream=sys.stdout,
        level=numeric,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,  # fuerza reconfiguración si basicConfig ya fue llamado
    )


def get_logger(name: str) -> logging.Logger:
    """
    Retorna un logger con el nombre dado (convencionalmente el __name__ del módulo).

    Args:
        name: Nombre del logger, típicamente __name__.

    Returns:
        Logger configurado.
    """
    return logging.getLogger(name)
