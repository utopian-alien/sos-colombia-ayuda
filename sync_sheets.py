import json
import os
import firebase_admin
from firebase_admin import credentials, db
from google.oauth2 import service_account
import gspread

# Cargar credenciales
service_account_raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
service_account_info = json.loads(service_account_raw)

# Inicializar Firebase Realtime Database
cred = credentials.Certificate(service_account_info)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juntosayudamos-col-default-rtdb.firebaseio.com/'
    })

# Conectar a Google Sheets
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
gspread_creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(gspread_creds)

# Sincronización
SHEET_ID = "1VCzTX1d1rKwbFryjm8YLYBlIaMiKG6eh3y5mZsie6h8"
sheet = gc.open_by_key(SHEET_ID).sheet1
rows = sheet.get_all_records()

ref = db.reference('ayudas')
# Borramos lo viejo para que el mapa solo muestre lo nuevo y correcto
ref.delete() 

print(f"📥 Sincronizando {len(rows)} registros...")

for row in rows:
    lugar = str(row.get("LUGAR", "sin_nombre")).strip()
    # Usamos un ID simple y limpio
    doc_id = "lugar_" + str(len(list(ref.get() or [])) + 1)
    
    data = {
        "lugar": lugar,
        "direccion": row.get("DIRECCIÓN", "Bogotá"),
        "necesita": row.get("SE NECESITAN VOLUNTARIOS", ""),
        "ciudad": "Bogotá",
        "latitud": 4.6097,
        "longitud": -74.0817
    }
    ref.child(doc_id).set(data)

print("✅ Sincronización completa.")
