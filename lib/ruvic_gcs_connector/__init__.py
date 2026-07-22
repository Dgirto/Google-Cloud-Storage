"""Conector Ruvic para gestión de objetos en Google Cloud Storage."""

from .client import GcsClient
from .config import ENV_PREFIX, GcsConfig
from .exceptions import (
    GcsAuthError,
    GcsConnectorError,
    GcsDataError,
    GcsNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "GcsAuthError",
    "GcsClient",
    "GcsConfig",
    "GcsConnectorError",
    "GcsDataError",
    "GcsNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
