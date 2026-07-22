"""Validación local del conector gcs: ejercita las 3 capacidades.

Uso:
    python validate_local.py

Requiere las variables RUVIC_GCS_* exportadas en el entorno, apuntando a
un bucket real donde la cuenta de servicio tenga permiso de lectura y
escritura. No necesita ningún objeto previo: sube uno de prueba, lo
lista y lo descarga.
"""

from ruvic_gcs_connector import GcsClient, setup_logging

setup_logging("INFO")
client = GcsClient()

print("== 1. Subir objeto de prueba ==")
uploaded = client.upload_object(
    "ruvic/validate_local/prueba.txt", "Contenido de prueba de validate_local.py"
)
print(f"  {uploaded}")

print("== 2. Listar objetos (prefijo ruvic/validate_local/) ==")
objects = client.list_objects(prefix="ruvic/validate_local/", limit=10)
for obj in objects:
    print(f"  {obj['name']} ({obj['size']} bytes, {obj['updated']})")
assert any(o["name"] == "ruvic/validate_local/prueba.txt" for o in objects), "No aparece el objeto subido"

print("== 3. Descargar el objeto ==")
downloaded = client.download_object("ruvic/validate_local/prueba.txt")
text = downloaded["content"].decode("utf-8")
print(f"  contenido={text!r} size={downloaded['size']}")
assert text == "Contenido de prueba de validate_local.py", "El contenido descargado no coincide"

print("\nTodo OK: upload_object, list_objects y download_object funcionan.")
