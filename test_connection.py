"""Prueba de conexión estándar del conector gcs.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_GCS_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Verifica acceso al bucket configurado usando las env vars RUVIC_GCS_*."""
    try:
        from ruvic_gcs_connector import (
            GcsAuthError,
            GcsClient,
            GcsDataError,
            GcsNetworkError,
        )
    except ImportError:
        return (
            False,
            "La librería ruvic-gcs-connector no está instalada. "
            "Instala con: pip install git+https://github.com/Dgirto/"
            "Google-Cloud-Storage.git#subdirectory=lib",
        )

    try:
        client = GcsClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except GcsAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except GcsNetworkError as exc:
        return False, f"Error de red: {exc}"
    except GcsDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return (True, f"Conexión exitosa al bucket {client.config.bucket!r}")


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
