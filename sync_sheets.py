import os
import json
import csv
import io
import requests
import firebase_admin
from firebase_admin import credentials, db

# Configuración de URLs y Constantes con tu ID real de Google Sheets
SHEET_ID = "1-hMGwC0XaSu5ddZ896gYyVRpmbPkVYg3NJ_6rSxK4Y8"
MAPBOX_TOKEN = "pk.eyJ1IjoidXRvcGlhbmFsaWVuIiwiYSI6ImNtc3J2cDUwYjAxZmMyeHB6c2c1enc2YnMifQ.KKhtf-Di1JSIhY5jxF0k1Q"

# Inicializar Firebase Admin usando el secreto de GitHub
if not firebase_admin._apps:
    service_account_info = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT"))
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://juntosayudamos-col-default-rtdb.firebaseio.com'
    })

def geocodificar(direccion):
    if not direccion or direccion.strip() == "":
        return 4.5709, -74.2973
    consulta = f"{direccion}, Colombia"
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(consulta)}.json?access_token={MAPBOX_TOKEN}&country=co&language=es&limit=1"
    try:
        res = requests.get(url).json()
        if res.get('features'):
            lon, lat = res['features'][0]['center']
            return lat, lon
    except Exception:
        pass
    return 4.5709, -74.2973

def ejecutar_sincronizacion_espejo():
    print("🔄 Iniciando sincronización espejo desde Google Sheets...")
    
    # 1. Descargar CSV de Google Sheets
    csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    res_sheets = requests.get(csv_url)
    if not res_sheets.ok:
        print("⚠️ No se pudo obtener la hoja de cálculo de Google Sheets.")
        return

    # 2. Parsear el CSV de manera segura con el módulo estándar de Python
    f = io.StringIO(res_sheets.text)
    lector = csv.reader(f)
    filas = list(lector)
    
    if not filas:
        print("⚠️ La hoja de Google Sheets está vacía.")
        return

    print(f"📊 {len(filas) - 1} filas de datos leídas (ignorando encabezado).")

    # 3. Construir el nuevo estado basado en Sheets
    nuevo_estado = {}
    for idx, columnas in enumerate(filas[1:]): # Ignorar la primera fila (encabezado)
        if not columnas or len(columnas) < 1:
            continue

        titulo = columnas[0].strip()
        detalle = " ".join([c.strip() for c in columnas[1:] if c.strip()])
        
        if not titulo:
            continue

        is_oferta = "🟢" in detalle or "sí voluntarios" in detalle.lower() or "necesitan voluntarios" in detalle.lower()
        lat, lng = geocodificar(titulo)

        key_id = f"sheet_node_{idx+1}"
        nuevo_estado[key_id] = {
            "modalidad": "ofrece" if is_oferta else "necesita",
            "ubicacion": f"{titulo}, Colombia",
            "tiposActivos": ["🙋‍♂️ Trabajo Voluntario / Mano de Obra"],
            "prioridad": "Alta" if "URGEN" in detalle else "Media",
            "descripcion": f"{titulo} | {detalle}",
            "lat": lat,
            "lng": lng,
            "contacto": "",
            "pin": "2026",
            "otroDetalle": detalle,
            "verificaciones": 3 if is_oferta else 1,
            "reportesCount": 0,
            "tiposInactivos": [],
            "origen": "google_sheets"
        }

    # 4. Conectar a Firebase
    ref = db.reference('solicitudes_ayuda')
    estado_actual = ref.get() or {}

    # 5. Sincronización Espejo: Eliminar registros que ya no están en Sheets
    for key, item in list(estado_actual.items()):
        if isinstance(item, dict) and item.get("origen") == "google_sheets":
            if key not in nuevo_estado:
                print(f"🗑️ Eliminando registro borrado en Sheets: {key}")
                ref.child(key).delete()

    # 6. Actualizar o insertar los registros vigentes
    ref.update(nuevo_estado)

    print("✅ ¡Sincronización Espejo Completada con Éxito!")

if __name__ == "__main__":
    ejecutar_sincronizacion_espejo()
