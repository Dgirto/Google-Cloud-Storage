"""Excepciones propias del conector Google Cloud Storage.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del SDK subyacente.
"""


class GcsConnectorError(Exception):
    """Error base del conector."""


class GcsAuthError(GcsConnectorError):
    """Credenciales inválidas o permisos IAM insuficientes."""


class GcsNetworkError(GcsConnectorError):
    """No se pudo alcanzar el servicio (red, timeout, error temporal de GCP)."""


class GcsDataError(GcsConnectorError):
    """La operación es válida pero el bucket/objeto no existe o los datos son inválidos."""
