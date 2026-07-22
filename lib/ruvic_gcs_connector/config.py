"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_GCS_.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

ENV_PREFIX = "RUVIC_GCS_"


@dataclass(frozen=True)
class GcsConfig:
    """Parámetros de conexión a Google Cloud Storage."""

    service_account_info: dict[str, Any]
    bucket: str
    connect_timeout: int = 10

    @classmethod
    def from_env(cls) -> "GcsConfig":
        """Construye la configuración desde las variables RUVIC_GCS_*.

        Raises:
            ValueError: si falta alguna variable obligatoria o el JSON de
                la cuenta de servicio no es válido.

        Ejemplo:
            >>> config = GcsConfig.from_env()
            >>> config.bucket
            'mi-bucket-produccion'
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("SERVICE_ACCOUNT_JSON", "BUCKET")
            if not os.environ.get(f"{ENV_PREFIX}{name}")
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector gcs: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )

        raw_json = os.environ[f"{ENV_PREFIX}SERVICE_ACCOUNT_JSON"]
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{ENV_PREFIX}SERVICE_ACCOUNT_JSON no contiene un JSON válido: {exc}. "
                "Verifica que copiaste el archivo de credenciales completo, sin "
                "recortar ni modificar su contenido."
            ) from exc

        missing_keys = [k for k in ("client_email", "private_key", "project_id") if k not in info]
        if missing_keys:
            raise ValueError(
                "El JSON de la cuenta de servicio no tiene el formato esperado "
                f"(faltan campos: {', '.join(missing_keys)}). Descárgalo de nuevo "
                "desde Google Cloud Console → IAM y administración → Cuentas de servicio."
            )

        return cls(
            service_account_info=info,
            bucket=os.environ[f"{ENV_PREFIX}BUCKET"],
            connect_timeout=int(os.environ.get(f"{ENV_PREFIX}CONNECT_TIMEOUT", "10")),
        )
