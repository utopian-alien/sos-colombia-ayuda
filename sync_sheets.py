import json
import os
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

ref = db.reference('solicitudes_ayuda')

# PASO CLAVE: Obtener lo que ya existe en Firebase para NO BORRAR los aportes de los usuarios
current_data = ref.get() or {}

# Filtrar y conservar SOLO los datos que NO vienen de Google Sheets (lo que la gente cargó a mano)
user_data = {}
for key, value in current_data.items():
    if isinstance(value, dict) and value.get("origen") != "google_sheets":
        user_data[key] = value

# Procesar los datos limpios del Excel
sheet_data = {}
sincronizados = 0

for i, row in enumerate(rows):
    try:
        lugar = str(row.get("LUGAR", "")).strip()
        direccion = str(row.get("DIRECCIÓN", "")).strip()

        # Omitir filas vacías o con "N/A"
        if not lugar or lugar.upper() == "N/A" or not direccion or direccion.upper() == "N/A":
            continue

        doc_id = f"sheet_registro_{i}"
        sheet_data[doc_id] = {
            "modalidad": "necesita",
            "ubicacion": lugar,
            "direccion": direccion,
            "descripcion": f"Dirección: {direccion} | Necesita: {row.get('SE NECESITAN VOLUNTARIOS', row.get('SE NECESITAN DONACIONES', ''))} | Notas: {row.get('NOTAS', '')}",
            "lat": 4.6097,
            "lng": -74.0817,
            "contacto": str(row.get("CONTACTO CLAVE", "")),
            "prioridad": "Media",
            "tiposActivos": ["🥣 Alimentos y Agua Potable"],
            "origen": "google_sheets"
        }
        sincronizados += 1
    except Exception as e:
        continue

# Combinar los datos de los usuarios + los registros actualizados del Excel
combined_data = {**user_data, **sheet_data}

# Guardar todo de forma segura sin destruir nada externo
ref.set(combined_data)

print(f"✅ Sincronización exitosa. Se conservaron los datos manuales y se actualizaron {sincronizados} registros de Google Sheets.")
