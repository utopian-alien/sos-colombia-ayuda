import json
import os
import urllib.request
import urllib.parse
import firebase_admin
from firebase_admin import credentials, db
from google.oauth2 import service_account
import gspread

# Credenciales
service_account_raw = os.getenv("FIREBASE_SERVICE_ACCOUNT")
service_account_info = json.loads(service_account_raw)
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred, {'databaseURL': 'https://juntosayudamos-col-default-rtdb.firebaseio.com/'})

# Auth Sheets
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
gspread_creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
gc = gspread.authorize(gspread_creds)

SHEET_ID = "1VCzTX1d1rKwbFryjm8YLYBlIaMiKG6eh3y5mZsie6h8"
sheet = gc.open_by_key(SHEET_ID).sheet1
rows = sheet.get_all_records()

# Referencias
ref_ayudas = db.reference('ayudas')
ref_solicitudes = db.reference('solicitudes_ayuda')

# RESCATE TOTAL: Leer nodos y combinarlos en un diccionario local
combined_data = {}

def load_and_merge(ref, label):
    data = ref.get()
    count = 0
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                # Usamos una clave única para que no se pisen
                combined_data[f"{label}_{k}"] = v
                count += 1
    print(f"📥 Cargados {count} registros desde {label}")

load_and_merge(ref_ayudas, "manual_ayudas")
load_and_merge(ref_solicitudes, "manual_solic")

print(f"✅ Total registros manuales rescatados: {len(combined_data)}")

# Mapbox
MAPBOX_TOKEN = "pk.eyJ1IjoidXRvcGlhbmFsaWVuIiwiYSI6ImNtc3J2cDUwYjAxZmMyeHB6c2c1enc2YnMifQ.KKhtf-Di1JSIhY5jxF0k1Q"

def get_coords(direccion, lugar):
    # Consulta optimizada para lugares o direcciones
    query = f"{direccion}, {lugar}, Bogotá, Colombia"
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{urllib.parse.quote(query)}.json?access_token={MAPBOX_TOKEN}&country=co&limit=1"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("features"):
                center = data["features"][0]["center"]
                return float(center[1]), float(center[0])
    except: pass
    return 4.6097, -74.0817

# Procesar Excel
excel_count = 0
for i, row in enumerate(rows):
    lugar = str(row.get("LUGAR", "")).strip()
    if not lugar or lugar.upper() in ["N/A", "NA", "-"]: continue
    
    lat, lng = get_coords(str(row.get("DIRECCIÓN", "")), lugar)
    
    # Estructura que tu JS espera
    combined_data[f"sheet_registro_{i}"] = {
        "modalidad": "necesita",
        "ubicacion": lugar,
        "descripcion": f"Dirección: {row.get('DIRECCIÓN')} | Notas: {row.get('NOTAS')}",
        "lat": lat,
        "lng": lng,
        "origen": "google_sheets"
    }
    excel_count += 1

# GUARDAR TODO
ref_solicitudes.set(combined_data)
print(f"🚀 Subidos {excel_count} registros de Excel. Total final en Firebase: {len(combined_data)}")
