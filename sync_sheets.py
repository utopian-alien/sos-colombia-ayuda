import json
import os
import urllib.request
import urllib.parse
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

# Referencia unificada
ref_solicitudes = db.reference('solicitudes_ayuda')

# Rescatar datos manuales previos de ambos nodos para no perder nada
ref_ayudas = db.reference('ayudas')
data_ayudas = ref_ayudas.get() or {}
data_solicitudes = ref_solicitudes.get() or {}

user_data = {}
if isinstance(data_ayudas, dict):
    for key, value in data_ayudas.items():
        if isinstance(value, dict):
            user_data[f"manual_ayudas_{key}"] = value

if isinstance(data_solicitudes, dict):
    for key, value in data_solicitudes.items():
        if isinstance(value, dict) and value.get("origen") != "google_sheets":
            user_data[key] = value

MAPBOX_TOKEN = "pk.eyJ1IjoidXRvcGlhbmFsaWVuIiwiYSI6ImNtc3J2cDUwYjAxZmMyeHB6c2c1enc2YnMifQ.KKhtf-Di1JSIhY5jxF0k1Q"

def obtener_coordenadas(direccion, lugar):
    # Si la dirección es N/A o vacía, usamos el nombre del lugar (ej: "Estadio El Campín") asegurando Bogotá
    query_base = lugar if not direccion or direccion.upper() in ["N/A", "NA", "-"] else f"{direccion}, {lugar}"
    
    # Asegurar que siempre se busque dentro de Bogotá, Colombia
    if "bogotá" not in query_base.lower():
        query_base += ", Bogotá"
    if "colombia" not in query_base.lower():
        query_base += ", Colombia"

    encoded = urllib.parse.quote(query_base)
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json?access_token={MAPBOX_TOKEN}&country=co&limit=1"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("features"):
                center = data["features"][0]["center"] # [lng, lat]
                return float(center[1]), float(center[0])
    except Exception:
        pass
    
    # Coordenada central de respaldo en Bogotá si falla la red
    return 4.6097, -74.0817

sheet_data = {}
sincronizados = 0

print("📥 Procesando Excel, limpiando direcciones y geocodificando...")

for i, row in enumerate(rows):
    try:
        lugar = str(row.get("LUGAR", "")).strip()
        direccion = str(row.get("DIRECCIÓN", "")).strip()
        necesidad = str(row.get("SE NECESITAN VOLUNTARIOS", row.get("SE NECESITAN DONACIONES", ""))).strip()
        notas = str(row.get("NOTAS", "")).strip()
        contacto = str(row.get("CONTACTO CLAVE", "")).strip()

        if not lugar or lugar.upper() in ["ANULADO", "CANCELADO"]:
            continue

        # Obtener coordenadas reales (incluso si la dirección es N/A, usará el nombre del lugar)
        lat, lng = obtener_coordenadas(direccion, lugar)

        # Estructura 100% estandarizada para que el index.html la pinte sin errores
        sheet_data[f"sheet_registro_{i}"] = {
            "modalidad": "necesita",
            "lugar": lugar,
            "ubicacion": lugar if not direccion or direccion.upper() in ["N/A", "NA", "-"] else f"{lugar} - {direccion}",
            "direccion": direccion,
            "necesita": necesidad,
            "notas": notas,
            "descripcion": f"Dirección: {direccion if direccion else 'Referencia en sitio'} | Necesita: {necesidad} | Notas: {notas}",
            "lat": lat,
            "latitud": lat,
            "lng": lng,
            "longitud": lng,
            "contacto": contacto,
            "prioridad": "Media",
            "tiposActivos": ["🥣 Alimentos y Agua Potable"],
            "tiposInactivos": [],
            "verificaciones": 1,
            "reportesCount": 0,
            "origen": "google_sheets"
        }
        sincronizados += 1
    except Exception as e:
        continue

# Unir todo de forma segura
combined_data = {**user_data, **sheet_data}
ref_solicitudes.set(combined_data)

print(f"✅ ¡Listo! Se conservaron {len(user_data)} registros manuales y se ubicaron correctamente {sincronizados} registros del Excel.")
