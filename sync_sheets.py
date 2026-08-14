import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
import gspread

# 1. Cargar credenciales de Firebase desde la Variable de Entorno (GitHub Secret)
service_account_raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
if not service_account_raw:
  raise ValueError(
      "❌ Error: La variable de entorno FIREBASE_SERVICE_ACCOUNT no está"
      " configurada."
  )

service_account_info = json.loads(service_account_raw)

# 2. Inicializar Firebase
cred = credentials.Certificate(service_account_info)
if not firebase_admin._apps:
  firebase_admin.initialize_app(cred)

db = firestore.client()

# 3. Conectar a Google Sheets usando la misma credencial
gc = gspread.authorize(cred)

# ID de tu Google Sheet complementario
SHEET_ID = "1VCzTX1d1rKwbFryjm8YLYBlIaMiKG6eh3y5mZsie6h8"
sheet = gc.open_by_key(SHEET_ID).sheet1  # O la pestaña correspondiente

# Obtener todos los registros del Excel
rows = sheet.get_all_records()

print(f"📥 Sincronizando {len(rows)} registros desde Google Sheets a Firebase...")

for index, row in enumerate(rows):
  # Extraemos los campos principales (ajusta los nombres según tus columnas exactas)
  lugar = row.get("LUGAR", "").strip()
  if not lugar:
    continue  # Si no hay lugar, saltar fila vacía

  # --- FORZAR UBICACIÓN A BOGOTÁ ---
  # Sobrescribimos o fijamos los datos geográficos para que el mapa los lea siempre en Bogotá
  data_to_upload = {
      "lugar": lugar,
      "direccion": row.get("DIRECCIÓN", "Bogotá"),
      "necesita": row.get(
          "SE NECESITAN VOLUNTARIOS", row.get("SE NECESITAN DONACIONES", "")
      ),
      "horarios": row.get("HORARIOS", ""),
      "actualizacion": row.get("HORA DE ACTUALIZACIÓN", ""),
      "notas": row.get("NOTAS", ""),
      "link": row.get("LINK DE INSCRIPCIÓN", row.get("Link de donaciones:", "")),
      "contacto": row.get("CONTACTO CLAVE", ""),
      "grupo": row.get("GRUPO DE WHATSAPP", ""),
      "insta": row.get("INSTAGRAM", ""),
      "funciones": row.get("FUNCIONES VOLUNTARIOS", ""),
      # Coordenadas y ciudad fijas en Bogotá
      "ciudad": "Bogotá",
      "ubicacion_formateada": "Bogotá, Colombia",
      "latitud": 4.6097,
      "longitud": -74.0817,
  }

  # Usar el nombre del lugar como ID único en Firebase (limpiando espacios/caracteres)
  doc_id = lugar.lower().replace(" ", "_").replace("/", "_")

  # Subir o actualizar en la colección de Firestore (ej: 'ayudas')
  db.collection("ayudas").document(doc_id).set(data_to_upload, merge=True)

print("✅ ¡Sincronización completada con éxito! Todo ubicado en Bogotá.")
