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

# RESCATE TOTAL: Leer absolutamente todo lo que existe antes de tocar nada
all_manual_data = {}
for data in [ref_ayudas.get(), ref_solicitudes.get()]:
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict): all_manual_data[k] = v

MAPBOX_TOKEN = "pk.eyJ1IjoidXRvcGlhbmFsaWVuIiwiYSI6ImNtc3J2cDUwYjAxZmMyeHB6c2c1enc2YnMifQ.KKhtf-Di1JSIhY5jxF0k1Q"

def get_coords(direccion, lugar):
    # Intentar búsqueda combinada
    queries = [f"{direccion}, {lugar}, Bogotá, Colombia", f"{lugar}, Bogotá, Colombia"]
    for q in queries:
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{urllib.parse.quote(q)}.json?access_token={MAPBOX_TOKEN}&country=co&limit=1"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                if data.get("features"):
                    center = data["features"][0]["center"]
                    return float(center[1]), float(center[0])
        except: continue
    return 4.6097, -74.0817 # Bogotá central

final_data = all_manual_data.copy()

for i, row in enumerate(rows):
    lugar = str(row.get("LUGAR", "")).strip()
    if not lugar or lugar.upper() in ["N/A", "NA", "-"]: continue
    
    lat, lng = get_coords(str(row.get("DIRECCIÓN", "")), lugar)
    
    final_data[f"sheet_{i}"] = {
        "modalidad": "necesita",
        "ubicacion": lugar,
        "lat": lat, "lng": lng,
        "descripcion": f"Dirección: {row.get('DIRECCIÓN')} | Notas: {row.get('NOTAS')}",
        "origen": "google_sheets"
    }

ref_solicitudes.set(final_data)
print(f"✅ Sincronizado. Total registros: {len(final_data)}")
