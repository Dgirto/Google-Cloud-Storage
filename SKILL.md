---
name: google-cloud-storage
description: >
  Usa la librería ruvic_gcs_connector para gestionar objetos en un bucket
  de Google Cloud Storage - listar objetos con prefijo (list_objects),
  subir contenido a una clave (upload_object) y descargar el contenido
  de un objeto (download_object). Úsala cuando el usuario pida subir,
  descargar o listar archivos en un bucket de Google Cloud Storage.
triggers:
- gcs
- google cloud storage
- bucket de gcp
- subir archivo
- descargar archivo
---

# Conector Google Cloud Storage (ruvic_gcs_connector)

Librería Python para gestionar objetos en un bucket de Google Cloud Storage. Está **preinstalada en el runtime** cuando el conector está configurado (si no, instálala con `pip install git+https://github.com/Dgirto/Google-Cloud-Storage.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de variables de entorno, disponibles cuando el conector `gcs` está configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_GCS_SERVICE_ACCOUNT_JSON` | JSON completo de la cuenta de servicio |
| `RUVIC_GCS_BUCKET` | Bucket sobre el que opera el conector |
| `RUVIC_GCS_CONNECT_TIMEOUT` | (opcional) timeout en segundos |

Si estas variables NO existen, el conector no está configurado: no generes código que lo use; indica al usuario que lo configure en **Settings → Conectores**.

## Este conector escribe (upload)

`upload_object` sube (o sobrescribe) contenido en el bucket configurado. No es de solo lectura.

## Conexión (siempre igual)

```python
from ruvic_gcs_connector import GcsClient

client = GcsClient()  # lee RUVIC_GCS_* del entorno automáticamente
```

Todas las operaciones actúan sobre el bucket único configurado en `RUVIC_GCS_BUCKET`.

## Capacidad 1 — Listar objetos

```python
objects = client.list_objects(prefix="reportes/", limit=50)
for obj in objects:
    print(f"{obj['name']}: {obj['size']} bytes, modificado {obj['updated']}")
```

## Capacidad 2 — Subir un objeto

```python
client.upload_object("reportes/resumen.txt", "Ventas: 1200 unidades")
client.upload_object("reportes/datos.csv", contenido_bytes, content_type="text/csv")
```

`content` acepta `str` (se codifica como UTF-8) o `bytes` directamente.

## Capacidad 3 — Descargar un objeto

```python
result = client.download_object("reportes/resumen.txt")
texto = result["content"].decode("utf-8")
print(texto)
```

`content` siempre viene como `bytes`; decodifica según el tipo de archivo.

## Manejo de errores

```python
from ruvic_gcs_connector import (
    GcsAuthError, GcsDataError, GcsNetworkError,
)

try:
    client.upload_object("clave", "contenido")
except GcsAuthError:
    print("Credenciales inválidas o sin permiso IAM sobre el bucket")
except GcsNetworkError:
    print("No se pudo alcanzar Google Cloud Storage — reintenta en unos segundos")
except GcsDataError as e:
    print(f"Error de datos: {e}")  # ej. el objeto no existe
```

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_GCS_*` (el constructor de `GcsClient` ya lo hace).
2. Nunca imprimas `RUVIC_GCS_SERVICE_ACCOUNT_JSON` en logs ni en la salida.
3. Usa `limit` razonable en `list_objects` (default 100, máximo 1000); para buckets grandes pide al usuario que acote el `prefix`.
4. `upload_object` siempre sobrescribe si el objeto ya existe; si eso no es lo que el usuario quiere, léelo primero con `download_object` para confirmar.
