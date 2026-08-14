import json
import os
import re
import firebase_admin
from firebase_admin import credentials, db
from google.oauth2 import service_account
import gspread

# 1. Cargar credenciales
service_account_raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
if not service_account_raw:
    raise ValueError("❌ Error: La variable de entorno FIREBASE_SERVICE_ACCOUNT no está configurada.")

service_account_info = json.loads(service_account_raw)

# 2. Inicializar Firebase
cred = credentials.Certificate(service_account_info)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juntosayudamos-col-default-rtdb.firebaseio.com/'
    })

# 3. Conectar a Google Sheets
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
gspread_creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(gspread_creds)

SHEET_ID = "1VCzTX1d1rKwbFryjm8YLYBlIaMiKG6eh3y5mZsie6h8"
sheet = gc.open_by_key(SHEET_ID).sheet1
rows = sheet.get_all_records()

print(f"📥 Sincronizando {len(rows)} registros a Realtime Database...")

ref = db.reference('ayudas')

for row in rows:
    lugar = row.get("LUGAR", "").strip()
    if not lugar:
        continue

    # Datos forzados a Bogotá
    data_to_upload = {
        "lugar": lugar,
        "direccion": f"{row.get('DIRECCIÓN', '')}, Bogotá, Colombia", # Se asegura que el mapa sepa que es Bogotá
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

    doc_id = lugar.lower()
    doc_id = re.sub(r'[\.\#\$\/\[\]]', '_', doc_id)
    doc_id = doc_id.replace(" ", "_")

    ref.child(doc_id).set(data_to_upload)

print("✅ ¡Sincronización completada!")
