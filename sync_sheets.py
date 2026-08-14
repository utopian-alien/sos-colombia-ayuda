import json
import os
import re
import firebase_admin
from firebase_admin import credentials, db
from google.oauth2 import service_account
import gspread

# 1. Cargar credenciales desde la Variable de Entorno (GitHub Secret)
service_account_raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
if not service_account_raw:
    raise ValueError("❌ Error: La variable de entorno FIREBASE_SERVICE_ACCOUNT no está configurada.")

service_account_info = json.loads(service_account_raw)

# 2. Inicializar Firebase Realtime Database
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

print(f"📥 Sincronizando {len(rows)} registros a la ruta 'solicitudes_ayuda'...")

# Referencia exacta a la ruta que tu index.html original lee
ref = db.reference('solicitudes_ayuda')

for row in rows:
    lugar = str(row.get("LUGAR", "")).strip()
    if not lugar:
        continue

    # Mapeo estructurado exactamente como tu frontend de 1500 líneas lo espera
    data_to_upload = {
        "modalidad": "necesita",
        "ubicacion": f"{lugar}, Bogotá, Colombia",
        "descripcion": f"Dirección: {row.get('DIRECCIÓN', 'Bogotá')} | Necesita: {row.get('SE NECESITAN VOLUNTARIOS', row.get('SE NECESITAN DONACIONES', ''))} | Notas: {row.get('NOTAS', '')}",
        "lat": 4.6097,
        "lng": -74.0817,
        "contacto": str(row.get("CONTACTO CLAVE", "")),
        "prioridad": "Media",
        "tiposActivos": ["🥣 Alimentos y Agua Potable"],
        "origen": "google_sheets"
    }

    # Limpiar ID para Firebase
    doc_id = lugar.lower()
    doc_id = re.sub(r'[\.\#\$\/\[\]]', '_', doc_id)
    doc_id = doc_id.replace(" ", "_")

    # Guardar en la base de datos
    ref.child(doc_id).set(data_to_upload)

print("✅ ¡Sincronización completada y adaptada para el mapa!")
