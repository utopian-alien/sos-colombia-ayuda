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

# DICCIONARIO SEGURO: Solo agregaremos cosas nuevas o actualizaremos, sin borrar lo viejo.
datos_a_subir = {}

# 1. RESCATE SEGURO: Mover lo de 'ayudas' a 'solicitudes_ayuda' SIN CAMBIAR SUS IDs
ayudas_data = ref_ayudas.get()
if isinstance(ayudas_data, dict):
    for k, v in ayudas_data.items():
        datos_a_subir[k] = v  # Mantiene el ID intacto (Ej: Istmina o Capilla UNAL)
    print(f"📥 Rescatados {len(ayudas_data)} registros del nodo 'ayudas'")

# Mapbox
MAPBOX_TOKEN = "pk.eyJ1IjoidXRvcGlhbmFsaWVuIiwiYSI6ImNtc3J2cDUwYjAxZmMyeHB6c2c1enc2YnMifQ.KKhtf-Di1JSIhY5jxF0k1Q"

def get_coords(direccion, lugar):
    # CORRECCIÓN: Se quitó el "Bogotá" quemado para que busque en toda Colombia.
    query = f"{direccion}, {lugar}, Colombia"
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{urllib.parse.quote(query)}.json?access_token={MAPBOX_TOKEN}&country=co&limit=1"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("features"):
                center = data["features"][0]["center"]
                return float(center[1]), float(center[0])
    except: pass
    return 4.6097, -74.0817

# 2. Procesar Excel
excel_count = 0
for i, row in enumerate(rows):
    lugar = str(row.get("LUGAR", "")).strip()
    if not lugar or lugar.upper() in ["N/A", "NA", "-"]: continue
    
    lat, lng = get_coords(str(row.get("DIRECCIÓN", "")), lugar)
    
    # Estructura que tu JS espera
    datos_a_subir[f"sheet_registro_{i}"] = {
        "modalidad": "necesita",
        "ubicacion": lugar,
        "descripcion": f"Dirección: {row.get('DIRECCIÓN')} | Notas: {row.get('NOTAS')}",
        "lat": lat,
        "lng": lng,
        "origen": "google_sheets"
    }
    excel_count += 1

# 3. LA SALVACIÓN: UPDATE EN LUGAR DE SET
# update() inyecta el Excel y los rescates al lado de lo que ya exista. NO BORRA NADA.
if datos_a_subir:
    ref_solicitudes.update(datos_a_subir)

print(f"🚀 ÉXITO: Inyectados {excel_count} registros de Excel a Firebase sin borrar los datos manuales.")
