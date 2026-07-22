# Conector Google Cloud Storage (CON-028)

Conector Ruvic para gestión de objetos en un bucket de Google Cloud
Storage. Permite listar objetos, subir contenido y descargar objetos.

## Instalación

```bash
pip install git+https://github.com/Dgirto/Google-Cloud-Storage.git#subdirectory=lib
```

Python 3.10+. Dependencia única: `google-cloud-storage>=2.14,<3.0`.

## Permisos requeridos en GCP

Crea una cuenta de servicio dedicada (no reutilizar una de otro
conector ni la cuenta de un usuario) con roles limitados al bucket
específico:

```bash
gsutil iam ch serviceAccount:ruvic-gcs@TU_PROYECTO.iam.gserviceaccount.com:roles/storage.objectViewer gs://mi-bucket-produccion
gsutil iam ch serviceAccount:ruvic-gcs@TU_PROYECTO.iam.gserviceaccount.com:roles/storage.objectCreator gs://mi-bucket-produccion
```

- `roles/storage.objectViewer` sobre el bucket: necesario para
  `gcs.list_objects` y `gcs.download`.
- `roles/storage.objectCreator` sobre el bucket: necesario para
  `gcs.upload`.
- No se otorgan roles de administración (`roles/storage.admin` a nivel
  de proyecto, eliminar buckets, cambiar políticas de acceso).

## Variables de entorno (`RUVIC_GCS_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_GCS_SERVICE_ACCOUNT_JSON` | Sí | JSON completo de la cuenta de servicio |
| `RUVIC_GCS_BUCKET` | Sí | Bucket sobre el que opera el conector |
| `RUVIC_GCS_CONNECT_TIMEOUT` | No (default `10`) | Timeout de conexión en segundos |

## Pruebas locales

Con GCP real (cuenta de servicio y bucket dedicado):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_GCS_SERVICE_ACCOUNT_JSON="$(cat ruta/a/tu-cuenta-de-servicio.json)"
export RUVIC_GCS_BUCKET=ruvic-test-bucket

python test_connection.py
python validate_local.py
```

Prueba también los casos de error (credenciales incorrectas, bucket
inexistente, objeto inexistente) y verifica que los mensajes sean claros.

## Notas de integración

- El conector opera sobre **un único bucket** (configurado en
  `RUVIC_GCS_BUCKET`), consistente con el principio de mínimo privilegio
  de los roles IAM recomendados.
- `upload_object` acepta `str` (se codifica UTF-8) o `bytes` directamente;
  `download_object` siempre retorna `bytes` en el campo `content`.
- No usa Application Default Credentials (ADC) del entorno: siempre
  construye las credenciales explícitamente desde el JSON de
  `RUVIC_GCS_SERVICE_ACCOUNT_JSON`, para evitar depender de configuración
  implícita de la máquina donde corre.
