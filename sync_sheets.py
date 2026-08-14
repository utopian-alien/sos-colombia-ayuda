import json
import os
import re
import firebase_admin
from firebase_admin import credentials, db
from google.oauth2 import service_account
import gspread

# 1. Cargar credenciales desde la Variable de Entorno
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

# 3. Conectar a Google Sheets
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
gspread_creds = service_account.Credentials.from_service_account_info(
    service_account_info, scopes=scopes
)
gc = gspread.authorize(gspread_creds)

SHEET_ID = "1VCzTX1d1rKwbFryjm8YLYBlIaMiKG6eh3y5mZsie6h8"
sheet = gc.open_by_key(SHEET_ID).sheet1
rows = sheet.get_all_records()

print(f"📥 Sincronizando registros desde Google Sheets...")

ref = db.reference('solicitudes_ayuda')

# PASO CRUCIAL: Obtener datos actuales para CONSERVAR los aportes manuales de los usuarios
current_data = ref.get() or {}
user_data = {}

if isinstance(current_data, dict):
    for key, value in current_data.items():
        if isinstance(value, dict) and value.get("origen") != "google_sheets":
            user_data[key] = value

sheet_data = {}
sincronizados = 0

for i, row in enumerate(rows):
    try:
        lugar = str(row.get("LUGAR", "")).strip()
        direccion = str(row.get("DIRECCIÓN", "")).strip()
        necesidad = str(row.get("SE NECESITAN VOLUNTARIOS", row.get("SE NECESITAN DONACIONES", ""))).strip()
        notas = str(row.get("NOTAS", "")).strip()
        contacto = str(row.get("CONTACTO CLAVE", "")).strip()

        # Omitir filas vacías o con "N/A" en lugar o dirección
        if not lugar or lugar.upper() == "N/A" or not direccion or direccion.upper() == "N/A":
            continue

        # Estructura con doble clave para garantizar compatibilidad total con tu frontend
        data_to_upload = {
            "modalidad": "necesita",
            "lugar": lugar,
            "ubicacion": lugar,
            "direccion": direccion,
            "necesita": necesidad,
            "notas": notas,
            "descripcion": f"Dirección: {direccion} | Necesita: {necesidad} | Notas: {notas}",
            "lat": 4.6097,
            "latitud": 4.6097,
            "lng": -74.0817,
            "longitud": -74.0817,
            "contacto": contacto,
            "prioridad": "Media",
            "origen": "google_sheets"
        }

        # ID único seguro para el registro de la hoja
        doc_id = f"sheet_registro_{i}"
        sheet_data[doc_id] = data_to_upload
        sincronizados += 1

    except Exception as e:
        print(f"⚠️ Aviso en fila {i}: {e}")
        continue

# Combinar datos manuales de usuarios + registros limpios del Excel
combined_data = {**user_data, **sheet_data}

# Actualizar Firebase de forma segura sin destruir nada
ref.set(combined_data)

print(f"✅ ¡Sincronización finalizada con éxito! Se conservaron los datos manuales y se actualizaron {sincronizados} registros válidos del Excel en 'solicitudes_ayuda'.")
