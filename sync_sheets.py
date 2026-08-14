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

print(f"📥 Procesando {len(rows)} registros desde Google Sheets...")

# Referencia a la ruta que lee tu web
ref = db.reference('solicitudes_ayuda')
ref.delete()  # Limpiar datos anteriores para evitar acumular basura

sincronizados = 0

for i, row in enumerate(rows):
    try:
        # Extraer y limpiar columnas de forma segura
        lugar = str(row.get("LUGAR", "")).strip()
        direccion = str(row.get("DIRECCIÓN", "")).strip()

        # Omitir si faltan datos o si son "N/A"
        if not lugar or lugar.upper() == "N/A" or not direccion or direccion.upper() == "N/A":
            continue

        # Estructura limpia para tu mapa, aprovechando la dirección estandarizada
        data_to_upload = {
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

        # ID único seguro basado en el índice de la fila para evitar errores de Firebase
        doc_id = f"registro_{i}"

        ref.child(doc_id).set(data_to_upload)
        sincronizados += 1

    except Exception as e:
        print(f"⚠️ Aviso: Se omitió la fila {i} debido a un formato inesperado: {e}")
        continue

print(f"✅ ¡Sincronización completada! Se subieron {sincronizados} registros limpios a Firebase.")
