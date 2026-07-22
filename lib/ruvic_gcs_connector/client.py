"""Cliente de gestión de objetos en Google Cloud Storage.

Capacidades:
- list_objects():    listar objetos de un bucket (con prefijo opcional).
- upload_object():   subir contenido a una clave del bucket.
- download_object(): descargar el contenido de un objeto.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_GCS_*
(ver config.GcsConfig.from_env). Prohibido hardcodearlas.

El conector opera sobre un único bucket configurado (principio de mínimo
privilegio: el rol IAM de la cuenta de servicio debe limitarse a ese
bucket).
"""

from __future__ import annotations

from typing import Any

from google.api_core.exceptions import (
    Forbidden,
    GoogleAPICallError,
    NotFound,
    ServiceUnavailable,
    Unauthorized,
)
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.cloud import storage
from google.oauth2 import service_account

from .config import GcsConfig
from .exceptions import (
    GcsAuthError,
    GcsConnectorError,
    GcsDataError,
    GcsNetworkError,
)
from .logging_utils import get_logger

_MAX_LIST_LIMIT = 1_000


def _validate_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        raise GcsDataError("key no puede estar vacía.")
    return key


def _wrap_error(exc: GoogleAPICallError, not_found_message: str) -> GcsConnectorError:
    """Traduce un error de la API de GCS a una excepción propia, sin dejar
    escapar nunca el tipo crudo del SDK."""
    if isinstance(exc, (Forbidden, Unauthorized)):
        return GcsAuthError(
            "Credenciales inválidas o sin permiso IAM suficiente sobre este "
            "bucket/objeto. Revisa el rol asignado a la cuenta de servicio."
        )
    if isinstance(exc, NotFound):
        return GcsDataError(not_found_message)
    if isinstance(exc, ServiceUnavailable):
        return GcsNetworkError(
            "Google Cloud Storage no respondió correctamente. Puede ser un "
            "límite de cuota temporal; reintenta en unos segundos."
        )
    return GcsDataError(f"Error de datos: {exc}")


class GcsClient:
    """Cliente de gestión de objetos en un bucket de Google Cloud Storage.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_GCS_* (comportamiento estándar en
            el runtime de la plataforma).

    Ejemplo:
        >>> client = GcsClient()            # lee RUVIC_GCS_* del entorno
        >>> client.list_objects(prefix="reportes/")
        [{'name': 'reportes/2026-07.csv', 'size': 15234, 'updated': '2026-07-17T10:00:00Z'}]
    """

    def __init__(self, config: GcsConfig | None = None) -> None:
        self.config = config or GcsConfig.from_env()
        self._logger = get_logger()
        self._client: storage.Client | None = None

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _get_client(self) -> storage.Client:
        if self._client is not None:
            return self._client
        try:
            credentials = service_account.Credentials.from_service_account_info(
                self.config.service_account_info
            )
        except (ValueError, KeyError) as exc:
            raise GcsAuthError(
                f"El JSON de la cuenta de servicio es inválido o le faltan campos: {exc}"
            ) from exc
        self._client = storage.Client(
            project=self.config.service_account_info.get("project_id"),
            credentials=credentials,
        )
        return self._client

    def _get_bucket(self) -> storage.Bucket:
        return self._get_client().bucket(self.config.bucket)

    def ping(self) -> bool:
        """Verifica la conexión comprobando acceso al bucket configurado
        (sin listar objetos).

        Returns:
            True si la conexión funciona.

        Raises:
            GcsAuthError / GcsNetworkError / GcsDataError según el fallo.
        """
        try:
            exists = self._get_bucket().exists()
        except (RefreshError, GoogleAuthError) as exc:
            raise GcsAuthError(
                "No se pudo autenticar con la cuenta de servicio. Verifica que "
                "el JSON de credenciales sea correcto y no esté revocado."
            ) from exc
        except GoogleAPICallError as exc:
            raise _wrap_error(
                exc, f"El bucket {self.config.bucket!r} no existe o no es accesible."
            ) from exc
        if not exists:
            raise GcsDataError(f"El bucket {self.config.bucket!r} no existe.")
        self._logger.info("Ping exitoso al bucket %s", self.config.bucket)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: listar objetos
    # ------------------------------------------------------------------ #

    def list_objects(self, prefix: str = "", limit: int = 100) -> list[dict[str, Any]]:
        """Lista los objetos del bucket configurado.

        Args:
            prefix: solo objetos cuya clave empiece con este prefijo
                (ej. "reportes/"). Default "" (todos).
            limit: máximo de objetos a retornar (default 100, máximo 1000).

        Returns:
            Lista de dicts: {"name", "size", "updated"} (updated en
            formato ISO 8601).

        Ejemplo:
            >>> client.list_objects(prefix="reportes/", limit=10)
            [{'name': 'reportes/2026-07.csv', 'size': 15234, 'updated': '2026-07-17T10:00:00Z'}]
        """
        limit = max(1, min(int(limit), _MAX_LIST_LIMIT))
        try:
            blobs = self._get_client().list_blobs(
                self.config.bucket, prefix=prefix or None, max_results=limit
            )
            result = [
                {
                    "name": blob.name,
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                }
                for blob in blobs
            ]
        except (RefreshError, GoogleAuthError) as exc:
            raise GcsAuthError(f"No se pudo autenticar: {exc}") from exc
        except GoogleAPICallError as exc:
            raise _wrap_error(
                exc, f"El bucket {self.config.bucket!r} no existe o no es accesible."
            ) from exc

        self._logger.info(
            "Se listaron %d objetos (prefix=%r) en %s", len(result), prefix, self.config.bucket
        )
        return result

    # ------------------------------------------------------------------ #
    # Capacidad 2: subir un objeto
    # ------------------------------------------------------------------ #

    def upload_object(
        self,
        key: str,
        content: bytes | str,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Sube contenido a una clave del bucket configurado (crea el
        objeto o sobrescribe uno existente con la misma clave).

        Args:
            key: nombre (ruta) del objeto dentro del bucket.
            content: contenido a subir. Un str se codifica como UTF-8.
            content_type: MIME type del objeto (opcional, ej. "text/csv").

        Returns:
            Dict con: name, size (bytes subidos).

        Ejemplo:
            >>> client.upload_object("reportes/resumen.txt", "Ventas: 1200")
            {'name': 'reportes/resumen.txt', 'size': 12}
        """
        key = _validate_key(key)
        body = content.encode("utf-8") if isinstance(content, str) else content
        try:
            blob = self._get_bucket().blob(key)
            blob.upload_from_string(body, content_type=content_type)
        except (RefreshError, GoogleAuthError) as exc:
            raise GcsAuthError(f"No se pudo autenticar: {exc}") from exc
        except GoogleAPICallError as exc:
            raise _wrap_error(
                exc, f"El bucket {self.config.bucket!r} no existe o no es accesible."
            ) from exc
        self._logger.info('Subido objeto "%s" (%d bytes)', key, len(body))
        return {"name": key, "size": len(body)}

    # ------------------------------------------------------------------ #
    # Capacidad 3: descargar un objeto
    # ------------------------------------------------------------------ #

    def download_object(self, key: str) -> dict[str, Any]:
        """Descarga el contenido de un objeto del bucket configurado.

        Args:
            key: nombre (ruta) del objeto dentro del bucket.

        Returns:
            Dict con: name, content (bytes), content_type, size.

        Ejemplo:
            >>> result = client.download_object("reportes/resumen.txt")
            >>> result["content"].decode("utf-8")
            'Ventas: 1200'
        """
        key = _validate_key(key)
        try:
            blob = self._get_bucket().blob(key)
            content = blob.download_as_bytes()
            blob.reload()
        except NotFound as exc:
            raise GcsDataError(
                f'El objeto "{key}" no existe en el bucket {self.config.bucket!r}.'
            ) from exc
        except (RefreshError, GoogleAuthError) as exc:
            raise GcsAuthError(f"No se pudo autenticar: {exc}") from exc
        except GoogleAPICallError as exc:
            raise _wrap_error(exc, f'El objeto "{key}" no existe.') from exc
        self._logger.info('Descargado objeto "%s" (%d bytes)', key, len(content))
        return {
            "name": key,
            "content": content,
            "content_type": blob.content_type,
            "size": len(content),
        }
