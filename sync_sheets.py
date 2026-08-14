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

# Referencias a ambos nodos en Firebase
ref_ayudas = db.reference('ayudas')
ref_solicitudes = db.reference('solicitudes_ayuda')

# Leer datos actuales de AMBAS rutas para no perder absolutamente nada
data_ayudas = ref_ayudas.get() or {}
data_solicitudes = ref_solicitudes.get() or {}

user_data = {}

# Recopilar registros de 'ayudas'
if isinstance(data_ayudas, dict):
    for key, value in data_ayudas.items():
        if isinstance(value, dict):
            # Si no es de google sheets, lo guardamos con prefijo para evitar que se pisen
            prefix = "" if value.get("origen") == "usuario" else "ayudas_"
            user_data[f"{prefix}{key}"] = value

# Recopilar registros de 'solicitudes_ayuda'
if isinstance(data_solicitudes, dict):
    for key, value in data_solicitudes.items():
        if isinstance(value, dict):
            user_data[key] = value

MAPBOX_TOKEN = "pk.eyJ1IjoidXRvcGlhbmFsaWVuIiwiYSI6ImNtc3J2cDUwYjAxZmMyeHB6c2c1enc2YnMifQ.KKhtf-Di1JSIhY5jxF0k1Q"

def obtener_coordenadas(direccion, lugar):
    texto = f"{direccion}, {lugar}, Colombia"
    encoded = urllib.parse.quote(texto)
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json?access_token={MAPBOX_TOKEN}&country=co&limit=1"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            if data.get("features"):
                center = data["features"][0]["center"]
                return float(center[1]), float(center[0])
    except Exception:
        pass
    return 4.6097, -74.0817

sheet_data = {}
sincronizados = 0

print("📥 Leyendo nodos 'ayudas' y 'solicitudes_ayuda' + procesando Excel...")

for i, row in enumerate(rows):
    try:
        lugar = str(row.get("LUGAR", "")).strip()
        direccion = str(row.get("DIRECCIÓN", "")).strip()
        necesidad = str(row.get("SE NECESITAN VOLUNTARIOS", row.get("SE NECESITAN DONACIONES", ""))).strip()
        notas = str(row.get("NOTAS", "")).strip()
        contacto = str(row.get("CONTACTO CLAVE", "")).strip()

        if not lugar or lugar.upper() in ["N/A", "NA", "-"]:
            continue

        lat, lng = obtener_coordenadas(direccion, lugar)

        sheet_data[f"sheet_registro_{i}"] = {
            "modalidad": "necesita",
            "lugar": lugar,
            "ubicacion": f"{lugar} ({direccion})",
            "direccion": direccion,
            "necesita": necesidad,
            "notas": notas,
            "descripcion": f"Dirección: {direccion} | Necesita: {necesidad} | Notas: {notas}",
            "lat": lat,
            "latitud": lat,
            "lng": lng,
            "longitud": lng,
            "contacto": contacto,
            "prioridad": "Media",
            "origen": "google_sheets"
        }
        sincronizados += 1
    except Exception as e:
        continue

# Unificar todo (Datos de ayudas + Datos de solicitudes_ayuda + Nuevos del Excel) en 'solicitudes_ayuda'
combined_data = {**user_data, **sheet_data}
ref_solicitudes.set(combined_data)

print(f"✅ ¡Sincronización completa! Se unificaron {len(user_data)} registros previos de ambos nodos y {sincronizados} del Excel en 'solicitudes_ayuda'.")
