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

# Todo va a una sola caja
ref_solicitudes = db.reference('solicitudes_ayuda')

datos_perfectos = {}

# 1. RESCATAR Y LAVAR A LA FUERZA TUS 20 DATOS MANUALES (Istmina, Capilla, etc.)
datos_actuales = ref_solicitudes.get()
if isinstance(datos_actuales, dict):
    for k, v in datos_actuales.items():
        # Tomar todo lo que no venga del Excel
        if isinstance(v, dict) and str(v.get("origen", "")) != "google_sheets":
            
            # Forzar visibilidad para que el mapa no los oculte
            v["desactivado"] = False
            
            # Arreglar comas por puntos en las coordenadas
            try:
                raw_lat = str(v.get("lat", v.get("latitud", 4.6097))).replace(',', '.')
                raw_lng = str(v.get("lng", v.get("longitud", -74.0817))).replace(',', '.')
                v["lat"] = float(raw_lat)
                v["lng"] = float(raw_lng)
            except:
                v["lat"] = 4.6097
                v["lng"] = -74.0817
            
            # Ponerle categoría obligatoria para que pase los filtros del mapa
            if "tiposActivos" not in v or not v["tiposActivos"]:
                v["tiposActivos"] = ["🥣 Alimentos y Agua Potable"]
                
            datos_perfectos[k] = v

# 2. PROCESAR EXCEL
MAPBOX_TOKEN = "pk.eyJ1IjoidXRvcGlhbmFsaWVuIiwiYSI6ImNtc3J2cDUwYjAxZmMyeHB6c2c1enc2YnMifQ.KKhtf-Di1JSIhY5jxF0k1Q"
def get_coords(direccion, lugar):
    # Buscar en toda Colombia, no solo Bogotá
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

for i, row in enumerate(rows):
    lugar = str(row.get("LUGAR", "")).strip()
    if not lugar or lugar.upper() in ["N/A", "NA", "-"]: continue
    
    lat, lng = get_coords(str(row.get("DIRECCIÓN", "")), lugar)
    
    datos_perfectos[f"sheet_registro_{i}"] = {
        "modalidad": "necesita",
        "ubicacion": lugar,
        "descripcion": f"Dirección: {row.get('DIRECCIÓN')} | Notas: {row.get('NOTAS')}",
        "lat": lat,
        "lng": lng,
        "origen": "google_sheets",
        "desactivado": False,
        "tiposActivos": ["🙋‍♂️ Trabajo Voluntario / Mano de Obra"]
    }

# 3. GUARDAR TODO UNIFICADO EN FIREBASE
ref_solicitudes.set(datos_perfectos)
print(f"🚀 ÉXITO: {len(datos_perfectos)} registros unificados y limpiados.")
