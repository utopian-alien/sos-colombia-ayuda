import json
import os
import firebase_admin
from firebase_admin import credentials, db
from google.oauth2 import service_account
import gspread

# 1. Cargar credenciales desde la Variable de Entorno (GitHub Secret)
service_account_raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
if not service_account_raw:
    raise ValueError("❌ Error: La variable de entorno FIREBASE_SERVICE_ACCOUNT no está configurada.")

service_account_info = json.loads(service_account_raw)

# 2. Inicializar Firebase para Realtime Database
cred = credentials.Certificate(service_account_info)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juntosayudamos-col-default-rtdb.firebaseio.com/'
    })

# 3. Conectar a Google Sheets usando Google Auth
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
gspread_creds = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=scopes
)
gc = gspread.authorize(gspread_creds)

# ID de tu Google Sheet
SHEET_ID = "1VCzTX1d1rKwbFryjm8YLYBlIaMiKG6eh3y5mZsie6h8"
sheet = gc.open_by_key(SHEET_ID).sheet1
rows = sheet.get_all_records()

print(f"📥 Sincronizando {len(rows)} registros a Realtime Database...")

# Referencia a la carpeta 'ayudas' en tu base de datos
ref = db.reference('ayudas')

for row in rows:
    lugar = row.get("LUGAR", "").strip()
    if not lugar:
        continue

    # Preparar los datos con Bogotá forzado
    data_to_upload = {
        "lugar": lugar,
        "direccion": row.get("DIRECCIÓN", "Bogotá"),
        "necesita": row.get("SE NECESITAN VOLUNTARIOS", row.get("SE NECESITAN DONACIONES", "")),
        "horarios": row.get("HORARIOS", ""),
        "actualizacion": row.get("HORA DE ACTUALIZACIÓN", ""),
        "notas": row.get("NOTAS", ""),
        "link": row.get("LINK DE INSCRIPCIÓN", row.get("Link de donaciones:", "")),
        "contacto": row.get("CONTACTO CLAVE", ""),
        "grupo": row.get("GRUPO DE WHATSAPP", ""),
        "insta": row.get("INSTAGRAM", ""),
        "funciones": row.get("FUNCIONES VOLUNTARIOS", ""),
        "ciudad": "Bogotá",
        "ubicacion_formateada": "Bogotá, Colombia",
        "latitud": 4.6097,
        "longitud": -74.0817,
    }

    # Crear ID único basado en el nombre del lugar
    doc_id = lugar.lower().replace(" ", "_").replace("/", "_")

    # Guardar en Realtime Database
    ref.child(doc_id).set(data_to_upload)

print("✅ ¡Sincronización completada en Realtime Database!")
